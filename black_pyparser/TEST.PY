from utils import timer
from utils.functions import MovingAverage, make_net

torch.cuda.current_device()
use_jit = torch.cuda.device_count() <= 1
if not use_jit:
    print("Multiple GPUs detected! Turning off JIT.")  # if
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
        if parent is None:
            if cfg.use_prediction_module:
                self.bn = nn.BatchNorm2d(out_channels)

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
