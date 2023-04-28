import torch, torchvision
import torch.nn as nn
import torch.nn.functional as F
from torchvision.models.resnet import Bottleneck
import numpy as np
from itertools import product
from math import sqrt
from typing import List
from collections import defaultdict
from data.config import cfg, mask_type
from layers import Detect
from layers.interpolate import InterpolateModule
from backbone import construct_backbone
import torch.backends.cudnn as cudnn
from utils import timer
from utils.functions import MovingAverage, make_net
torch.cuda.current_device()
use_jit = torch.cuda.device_count() <= 1
if not use_jit:

	print("Multiple GPUs detected! Turning off JIT.")
	

ScriptModuleWrapper = torch.jit.ScriptModule if use_jit else nn.Module
script_method_wrapper = torch.jit.script_method if use_jit else lambda fn, _rcn=None: fn
class Concat(nn.Module):
	
	
	
	def __init__(self, nets, extra_params):
		
		
		
			super().__init__()
			self.nets = nn.ModuleList(nets)
			self.extra_params = extra_params
			
		
	def forward(self, x):
		
		
		
			return torch.cat([net(x) for net in self.nets], dim=1, **self.extra_params)
			
		
		
	
prior_cache = defaultdict(lambda: None)
class PredictionModule(nn.Module):
	
	
	
	def __init__(
		
		
		
			self,
			in_channels,
			out_channels=1024,
			aspect_ratios=[[1]],
			scales=[1],
			parent=None,
			index=0,
			):
			super().__init__()
			self.num_classes = cfg.num_classes
			self.mask_dim = cfg.mask_dim
			self.num_priors = sum(len(x) * len(scales) for x in aspect_ratios)
			self.parent = [parent]
			self.index = index
			self.num_heads = cfg.num_heads
			if (
			
				cfg.mask_proto_split_prototypes_by_head
				and cfg.mask_type == mask_type.lincomb
				):
				self.mask_dim = self.mask_dim // self.num_heads
				
			if cfg.mask_proto_prototypes_as_features:
			
				in_channels += self.mask_dim
				
			if parent is None:
			
				if cfg.extra_head_net is None:
				
					out_channels = in_channels
				else:
					self.upfeature, out_channels = make_net(in_channels, cfg.extra_head_net)
					
				if cfg.use_prediction_module:
				
					self.block = Bottleneck(out_channels, out_channels // 4)
					self.conv = nn.Conv2d(
					out_channels, out_channels, kernel_size=1, bias=True
					)
					self.bn = nn.BatchNorm2d(out_channels)
					
				self.bbox_layer = nn.Conv2d(
				out_channels, self.num_priors * 4, **cfg.head_layer_params
				)
				self.conf_layer = nn.Conv2d(
				out_channels,
				self.num_priors * self.num_classes,
				**cfg.head_layer_params
				)
				self.mask_layer = nn.Conv2d(
				out_channels, self.num_priors * self.mask_dim, **cfg.head_layer_params
				)
				if cfg.use_mask_scoring:
				
					self.score_layer = nn.Conv2d(
					out_channels, self.num_priors, **cfg.head_layer_params
					)
					
				if cfg.use_instance_coeff:
				
					self.inst_layer = nn.Conv2d(
					out_channels,
					self.num_priors * cfg.num_instance_coeffs,
					**cfg.head_layer_params
					)
					
			def make_extra(num_layers):
				
				
				
					if num_layers == 0:
					
						return lambda x: x
					else:
						return nn.Sequential(
						*sum(
						[
						[
						nn.Conv2d(
						out_channels,
						out_channels,
						kernel_size=3,
						padding=1,
						),
						nn.ReLU(inplace=True),
						]
						for _ in range(num_layers)
						],
						[],
						)
						)
						
					
				self.bbox_extra, self.conf_extra, self.mask_extra = [
				make_extra(x) for x in cfg.extra_layers
				]
				if cfg.mask_type == mask_type.lincomb and cfg.mask_proto_coeff_gate:
				
					self.gate_layer = nn.Conv2d(
					out_channels,
					self.num_priors * self.mask_dim,
					kernel_size=3,
					padding=1,
					)
					
				
			self.aspect_ratios = aspect_ratios
			self.scales = scales
			self.priors = None
			self.last_conv_size = None
			self.last_img_size = None
			
		
	def forward(self, x):
		
		
		
			src = self if self.parent[0] is None else self.parent[0]
			conv_h = x.size(2)
			conv_w = x.size(3)
			if cfg.extra_head_net is not None:
			
				x = src.upfeature(x)
				
			if cfg.use_prediction_module:
			
				a = src.block(x)
				b = src.conv(x)
				b = src.bn(b)
				b = F.relu(b)
				x = a + b
				
			bbox_x = src.bbox_extra(x)
			conf_x = src.conf_extra(x)
			mask_x = src.mask_extra(x)
			bbox = (
			src.bbox_layer(bbox_x)
			.permute(0, 2, 3, 1)
			.contiguous()
			.view(x.size(0), -1, 4)
			)
			conf = (
			src.conf_layer(conf_x)
			.permute(0, 2, 3, 1)
			.contiguous()
			.view(x.size(0), -1, self.num_classes)
			)
			if cfg.eval_mask_branch:
			
				mask = (
				src.mask_layer(mask_x)
				.permute(0, 2, 3, 1)
				.contiguous()
				.view(x.size(0), -1, self.mask_dim)
				)
			else:
				mask = torch.zeros(
				x.size(0), bbox.size(1), self.mask_dim, device=bbox.device
				)
				
			if cfg.use_mask_scoring:
			
				score = (
				src.score_layer(x)
				.permute(0, 2, 3, 1)
				.contiguous()
				.view(x.size(0), -1, 1)
				)
				
			if cfg.use_instance_coeff:
			
				inst = (
				src.inst_layer(x)
				.permute(0, 2, 3, 1)
				.contiguous()
				.view(x.size(0), -1, cfg.num_instance_coeffs)
				)
				
			if cfg.use_yolo_regressors:
			
				bbox[:, :, :2] = torch.sigmoid(bbox[:, :, :2]) - 0.5
				bbox[:, :, 0] /= conv_w
				bbox[:, :, 1] /= conv_h
				
			if cfg.eval_mask_branch:
			
				if cfg.mask_type == mask_type.direct:
				
					mask = torch.sigmoid(mask)
					
			elif cfg.mask_type == mask_type.lincomb:
				mask = cfg.mask_proto_coeff_activation(mask)
				if cfg.mask_proto_coeff_gate:
				
					gate = (
					src.gate_layer(x)
					.permute(0, 2, 3, 1)
					.contiguous()
					.view(x.size(0), -1, self.mask_dim)
					)
					mask = mask * torch.sigmoid(gate)
					
				
			if (
			
				cfg.mask_proto_split_prototypes_by_head
				and cfg.mask_type == mask_type.lincomb
				):
				mask = F.pad(
				mask,
				(
				self.index * self.mask_dim,
				(self.num_heads - self.index - 1) * self.mask_dim,
				),
				mode="constant",
				value=0,
				)
				
			priors = self.make_priors(conv_h, conv_w, x.device)
			preds = {"loc": bbox, "conf": conf, "mask": mask, "priors": priors}
			if cfg.use_mask_scoring:
			
				preds["score"] = score
				
			if cfg.use_instance_coeff:
			
				preds["inst"] = inst
				
			return preds
			
		
	def make_priors(self, conv_h, conv_w, device):
		
		
		
			"""Note that priors are [x,y,width,height] where (x,y) is the center of the box."""
			global prior_cache
			size = (conv_h, conv_w)
			with timer.env("makepriors"):
			if self.last_img_size != (cfg._tmp_img_w, cfg._tmp_img_h):
			
				prior_data = []
				for j, i in product(range(conv_h), range(conv_w)):
				x = (i + 0.5) / conv_w
				y = (j + 0.5) / conv_h
				for ars in self.aspect_ratios:
				for scale in self.scales:
				for ar in ars:
				if not cfg.backbone.preapply_sqrt:
				
					ar = sqrt(ar)
					
				if cfg.backbone.use_pixel_scales:
				
					w = scale * ar / cfg.max_size
					h = scale / ar / cfg.max_size
				else:
					w = scale * ar / conv_w
					h = scale / ar / conv_h
					
				if cfg.backbone.use_square_anchors:
				
					h = w
					
				prior_data += [x, y, w, h]
				self.priors = (
				torch.Tensor(prior_data, device=device).view(-1, 4).detach()
				)
				self.priors.requires_grad = False
				self.last_img_size = (cfg._tmp_img_w, cfg._tmp_img_h)
				self.last_conv_size = (conv_w, conv_h)
				prior_cache[size] = None
				
		elif self.priors.device != device:
			if prior_cache[size] is None:
			
				prior_cache[size] = {}
				
			if device not in prior_cache[size]:
			
				prior_cache[size][device] = self.priors.to(device)
				
			self.priors = prior_cache[size][device]
			return self.priors
			
		
		
	
class FPN(ScriptModuleWrapper):
	
	
	
		__constants__ = [
		"interpolation_mode",
		"num_downsample",
		"use_conv_downsample",
		"relu_pred_layers",
		"lat_layers",
		"pred_layers",
		"downsample_layers",
		"relu_downsample_layers",
		]
	def __init__(self, in_channels):
		
		
		
			super().__init__()
			self.lat_layers = nn.ModuleList(
			[
			nn.Conv2d(x, cfg.fpn.num_features, kernel_size=1)
			for x in reversed(in_channels)
			]
			)
			padding = 1 if cfg.fpn.pad else 0
			self.pred_layers = nn.ModuleList(
			[
			nn.Conv2d(
			cfg.fpn.num_features,
			cfg.fpn.num_features,
			kernel_size=3,
			padding=padding,
			)
			for _ in in_channels
			]
			)
			if cfg.fpn.use_conv_downsample:
			
				self.downsample_layers = nn.ModuleList(
				[
				nn.Conv2d(
				cfg.fpn.num_features,
				cfg.fpn.num_features,
				kernel_size=3,
				padding=1,
				stride=2,
				)
				for _ in range(cfg.fpn.num_downsample)
				]
				)
				
			self.interpolation_mode = cfg.fpn.interpolation_mode
			self.num_downsample = cfg.fpn.num_downsample
			self.use_conv_downsample = cfg.fpn.use_conv_downsample
			self.relu_downsample_layers = cfg.fpn.relu_downsample_layers
			self.relu_pred_layers = cfg.fpn.relu_pred_layers
			
		
		@script_method_wrapper
	def forward(self, convouts: List[torch.Tensor]):
		
		
		
			out = []
			x = torch.zeros(1, device=convouts[0].device)
			for i in range(len(convouts)):
			out.append(x)
			j = len(convouts)
			for lat_layer in self.lat_layers:
			j -= 1
			if j < len(convouts) - 1:
			
				_, _, h, w = convouts[j].size()
				x = F.interpolate(
				x, size=(h, w), mode=self.interpolation_mode, align_corners=False
				)
				
			x = x + lat_layer(convouts[j])
			out[j] = x
			j = len(convouts)
			for pred_layer in self.pred_layers:
			j -= 1
			out[j] = pred_layer(out[j])
			if self.relu_pred_layers:
			
				F.relu(out[j], inplace=True)
				
			cur_idx = len(out)
			if self.use_conv_downsample:
			
				for downsample_layer in self.downsample_layers:
				out.append(downsample_layer(out[-1]))
			else:
				for idx in range(self.num_downsample):
				out.append(nn.functional.max_pool2d(out[-1], 1, stride=2))
				
			if self.relu_downsample_layers:
			
				for idx in range(len(out) - cur_idx):
				out[idx] = F.relu(out[idx + cur_idx], inplace=False)
				
			return out
			
		
		
	
class FastMaskIoUNet(ScriptModuleWrapper):
	
	
	
	def __init__(self):
		
		
		
			super().__init__()
			input_channels = 1
			last_layer = [(cfg.num_classes - 1, 1, {})]
			self.maskiou_net, _ = make_net(
			input_channels, cfg.maskiou_net + last_layer, include_last_relu=True
			)
			
		
	def forward(self, x):
		
		
		
			x = self.maskiou_net(x)
			maskiou_p = F.max_pool2d(x, kernel_size=x.size()[2:]).squeeze(-1).squeeze(-1)
			return maskiou_p
			
		
		
	
class Yolact(nn.Module):
	
	
	
	def __init__(self):
		
		
		
			super().__init__()
			self.backbone = construct_backbone(cfg.backbone)
			if cfg.freeze_bn:
			
				self.freeze_bn()
				
			if cfg.mask_type == mask_type.direct:
			
				cfg.mask_dim = cfg.mask_size**2
				
		elif cfg.mask_type == mask_type.lincomb:
			if cfg.mask_proto_use_grid:
			
				self.grid = torch.Tensor(np.load(cfg.mask_proto_grid_file))
				self.num_grids = self.grid.size(0)
			else:
				self.num_grids = 0
				
			self.proto_src = cfg.mask_proto_src
			if self.proto_src is None:
			
				in_channels = 3
				
		elif cfg.fpn is not None:
			in_channels = cfg.fpn.num_features
		else:
			in_channels = self.backbone.channels[self.proto_src]
			in_channels += self.num_grids
			self.proto_net, cfg.mask_dim = make_net(
			in_channels, cfg.mask_proto_net, include_last_relu=False
			)
			if cfg.mask_proto_bias:
			
				cfg.mask_dim += 1
				
			self.selected_layers = cfg.backbone.selected_layers
			src_channels = self.backbone.channels
			if cfg.use_maskiou:
			
				self.maskiou_net = FastMaskIoUNet()
				
			if cfg.fpn is not None:
			
				self.fpn = FPN([src_channels[i] for i in self.selected_layers])
				self.selected_layers = list(
				range(len(self.selected_layers) + cfg.fpn.num_downsample)
				)
				src_channels = [cfg.fpn.num_features] * len(self.selected_layers)
				
			self.prediction_layers = nn.ModuleList()
			cfg.num_heads = len(self.selected_layers)
			for idx, layer_idx in enumerate(self.selected_layers):
			parent = None
			if cfg.share_prediction_module and idx > 0:
			
				parent = self.prediction_layers[0]
				
			pred = PredictionModule(
			src_channels[layer_idx],
			src_channels[layer_idx],
			aspect_ratios=cfg.backbone.pred_aspect_ratios[idx],
			scales=cfg.backbone.pred_scales[idx],
			parent=parent,
			index=idx,
			)
			self.prediction_layers.append(pred)
			if cfg.use_class_existence_loss:
			
				self.class_existence_fc = nn.Linear(src_channels[-1], cfg.num_classes - 1)
				
			if cfg.use_semantic_segmentation_loss:
			
				self.semantic_seg_conv = nn.Conv2d(
				src_channels[0], cfg.num_classes - 1, kernel_size=1
				)
				
			self.detect = Detect(
			cfg.num_classes,
			bkg_label=0,
			top_k=cfg.nms_top_k,
			conf_thresh=cfg.nms_conf_thresh,
			nms_thresh=cfg.nms_thresh,
			)
			
		
	def save_weights(self, path):
		
		
		
			"""Saves the model's weights using compression because the file sizes were getting too big."""
			torch.save(self.state_dict(), path)
			
		
	def load_weights(self, path):
		
		
		
			"""Loads weights from a compressed save file."""
			state_dict = torch.load(path)
			for key in list(state_dict.keys()):
			if key.startswith("backbone.layer") and not key.startswith(
			
				"backbone.layers"
				):
				del state_dict[key]
				
			if key.startswith("fpn.downsample_layers."):
			
				if (
				
					cfg.fpn is not None
					and int(key.split(".")[2]) >= cfg.fpn.num_downsample
					):
					del state_dict[key]
					
				
			self.load_state_dict(state_dict)
			
		
	def init_weights(self, backbone_path):
		
		
		
			"""Initialize weights for training."""
			self.backbone.init_backbone(backbone_path)
			conv_constants = getattr(nn.Conv2d(1, 1, 1), "__constants__")
		def all_in(x, y):
			
			
			
				for _x in x:
				if _x not in y:
				
					return False
					
				return True
				
			
			for name, module in self.named_modules():
			is_script_conv = False
			if "Script" in type(module).__name__:
			
				if hasattr(module, "original_name"):
				
					is_script_conv = "Conv" in module.original_name
				else:
					is_script_conv = all_in(
					module.__dict__["_constants_set"], conv_constants
					) and all_in(conv_constants, module.__dict__["_constants_set"])
					
				
			is_conv_layer = isinstance(module, nn.Conv2d) or is_script_conv
			if is_conv_layer and module not in self.backbone.backbone_modules:
			
				nn.init.xavier_uniform_(module.weight.data)
				if module.bias is not None:
				
					if cfg.use_focal_loss and "conf_layer" in name:
					
						if not cfg.use_sigmoid_focal_loss:
						
							module.bias.data[0] = np.log(
							(1 - cfg.focal_loss_init_pi) / cfg.focal_loss_init_pi
							)
							module.bias.data[1:] = -np.log(module.bias.size(0) - 1)
						else:
							module.bias.data[0] = -np.log(
							cfg.focal_loss_init_pi / (1 - cfg.focal_loss_init_pi)
							)
							module.bias.data[1:] = -np.log(
							(1 - cfg.focal_loss_init_pi) / cfg.focal_loss_init_pi
							)
							
					else:
						module.bias.data.zero_()
						
					
				
			
		
	def train(self, mode=True):
		
		
		
			super().train(mode)
			if cfg.freeze_bn:
			
				self.freeze_bn()
				
			
		
	def freeze_bn(self, enable=False):
		
		
		
			"""Adapted from https://discuss.pytorch.org/t/how-to-train-with-frozen-batchnorm/12106/8"""
			for module in self.modules():
			if isinstance(module, nn.BatchNorm2d):
			
				module.train() if enable else module.eval()
				module.weight.requires_grad = enable
				module.bias.requires_grad = enable
				
			
		
	def forward(self, x):
		
		
		
			"""The input should be of size [batch_size, 3, img_h, img_w]"""
			_, _, img_h, img_w = x.size()
			cfg._tmp_img_h = img_h
			cfg._tmp_img_w = img_w
			with timer.env("backbone"):
			outs = self.backbone(x)
			if cfg.fpn is not None:
			
				with timer.env("fpn"):
				outs = [outs[i] for i in cfg.backbone.selected_layers]
				outs = self.fpn(outs)
				
			proto_out = None
			if cfg.mask_type == mask_type.lincomb and cfg.eval_mask_branch:
			
				with timer.env("proto"):
				proto_x = x if self.proto_src is None else outs[self.proto_src]
				if self.num_grids > 0:
				
					grids = self.grid.repeat(proto_x.size(0), 1, 1, 1)
					proto_x = torch.cat([proto_x, grids], dim=1)
					
				proto_out = self.proto_net(proto_x)
				proto_out = cfg.mask_proto_prototype_activation(proto_out)
				if cfg.mask_proto_prototypes_as_features:
				
					proto_downsampled = proto_out.clone()
					if cfg.mask_proto_prototypes_as_features_no_grad:
					
						proto_downsampled = proto_out.detach()
						
					
				proto_out = proto_out.permute(0, 2, 3, 1).contiguous()
				if cfg.mask_proto_bias:
				
					bias_shape = [x for x in proto_out.size()]
					bias_shape[-1] = 1
					proto_out = torch.cat([proto_out, torch.ones(*bias_shape)], -1)
					
				
			with timer.env("pred_heads"):
			pred_outs = {"loc": [], "conf": [], "mask": [], "priors": []}
			if cfg.use_mask_scoring:
			
				pred_outs["score"] = []
				
			if cfg.use_instance_coeff:
			
				pred_outs["inst"] = []
				
			for idx, pred_layer in zip(self.selected_layers, self.prediction_layers):
			pred_x = outs[idx]
			if (
			
				cfg.mask_type == mask_type.lincomb
				and cfg.mask_proto_prototypes_as_features
				):
				proto_downsampled = F.interpolate(
				proto_downsampled,
				size=outs[idx].size()[2:],
				mode="bilinear",
				align_corners=False,
				)
				pred_x = torch.cat([pred_x, proto_downsampled], dim=1)
				
			if (
			
				cfg.share_prediction_module
				and pred_layer is not self.prediction_layers[0]
				):
				pred_layer.parent = [self.prediction_layers[0]]
				
			p = pred_layer(pred_x)
			for k, v in p.items():
			pred_outs[k].append(v)
			for k, v in pred_outs.items():
			pred_outs[k] = torch.cat(v, -2)
			if proto_out is not None:
			
				pred_outs["proto"] = proto_out
				
			if self.training:
			
				if cfg.use_class_existence_loss:
				
					pred_outs["classes"] = self.class_existence_fc(
					outs[-1].mean(dim=(2, 3))
					)
					
				if cfg.use_semantic_segmentation_loss:
				
					pred_outs["segm"] = self.semantic_seg_conv(outs[0])
					
				return pred_outs
			else:
				if cfg.use_mask_scoring:
				
					pred_outs["score"] = torch.sigmoid(pred_outs["score"])
					
				if cfg.use_focal_loss:
				
					if cfg.use_sigmoid_focal_loss:
					
						pred_outs["conf"] = torch.sigmoid(pred_outs["conf"])
						if cfg.use_mask_scoring:
						
							pred_outs["conf"] *= pred_outs["score"]
							
						
				elif cfg.use_objectness_score:
					objectness = torch.sigmoid(pred_outs["conf"][:, :, 0])
					pred_outs["conf"][:, :, 1:] = objectness[:, :, None] * F.softmax(
					pred_outs["conf"][:, :, 1:], -1
					)
					pred_outs["conf"][:, :, 0] = 1 - objectness
				else:
					pred_outs["conf"] = F.softmax(pred_outs["conf"], -1)
				else:
					if cfg.use_objectness_score:
					
						objectness = torch.sigmoid(pred_outs["conf"][:, :, 0])
						pred_outs["conf"][:, :, 1:] = (objectness > 0.10)[
						..., None
						] * F.softmax(pred_outs["conf"][:, :, 1:], dim=-1)
					else:
						pred_outs["conf"] = F.softmax(pred_outs["conf"], -1)
						
					
				return self.detect(pred_outs, self)
				
			
		
		
	

if __name__ == "__main__":

	from utils.functions import init_console
	init_console()
	import sys
	if len(sys.argv) > 1:
	
		from data.config import set_cfg
		set_cfg(sys.argv[1])
		
	net = Yolact()
	net.train()
	net.init_weights(backbone_path="weights/" + "yolact_resnet50_54_800000.pth")
	net = net.cuda()
	torch.set_default_tensor_type("torch.cuda.FloatTensor")
	x = torch.zeros((1, 3, cfg.max_size, cfg.max_size))
	y = net(x)
	for p in net.prediction_layers:
	print(p.last_conv_size)
	print()
	for k, a in y.items():
	print(k + ": ", a.size(), torch.sum(a))
	exit()
	net(x)
	avg = MovingAverage()
	try:
	
		while True:
		timer.reset()
		with timer.env("everything else"):
		net(x)
		avg.add(timer.total_time())
		print("\033[2J")
		timer.print_stats()
		print(
		"Avg fps: %.2f\tAvg ms: %.2f "
		% (1 / avg.get_avg(), avg.get_avg() * 1000)
		)
		
except KeyboardInterrupt:
	pass
	

#  Export  Date: 12:31:25 AM - 28:Apr:2023.

