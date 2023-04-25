from utils import timer
from utils.functions import MovingAverage, make_net


torch.cuda.current_device()


use_jit = torch.cuda.device_count() <= 1
if not use_jit:
    print("Multiple GPUs detected! Turning off JIT.")
# if

ScriptModuleWrapper = torch.jit.ScriptModule if use_jit else nn.Module
script_method_wrapper = torch.jit.script_method if use_jit else lambda fn, _rcn=None: fn


class Concat(nn.Module):
    def __init__(self, nets, extra_params):
        super().__init__()

        self.nets = nn.ModuleList(nets)
        self.extra_params = extra_params

    def forward(self, x):
        return torch.cat([net(x) for net in self.nets], dim=1, **self.extra_params)


class PredictionModule(nn.Module):
    """
    The (c) prediction module adapted from DSSD:
    https://arxiv.org/pdf/1701.06659.pdf

    Note that this is slightly different to the module in the paper
    because the Bottleneck block actually has a 3x3 convolution in
    the middle instead of a 1x1 convolution. Though, I really can't
    be arsed to implement it myself, and, who knows, this might be
    better.

    Args:
    - in_channels:   The input feature size.
    - out_channels:  The output feature size (must be a multiple of 4).
    - aspect_ratios: A list of lists of priorbox aspect ratios (one list per scale).
    - scales:        A list of priorbox scales relative to this layer's convsize.
    For instance: If this layer has convouts of size 30x30 for
    an image of size 600x600, the 'default' (scale
    of 1) for this layer would produce bounding
    boxes with an area of 20x20px. If the scale is
    .5 on the other hand, this layer would consider
    bounding boxes with area 10x10px, etc.
    - parent:        If parent is a PredictionModule, this module will use all the layers
    from parent instead of from this module.
    """

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
        self.last_img_size = None  ###-------------------------DONE


prior_cache = defaultdict(lambda: None)
