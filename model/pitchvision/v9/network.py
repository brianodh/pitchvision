"""The v9 head: one convolution, pooled at several temporal widths, then a small classifier.

Identical in structure to v8's head; only the input width differs (368 instead of 512), because
it consumes T-DEED's pre-classifier representation rather than ResNet-152 features reduced by PCA.
Architecture matches the training code exactly, so checkpoints load without remapping.
"""
import numpy as np
import torch
import torch.nn as nn

FPS125 = 12.5                       # T-DEED's native rate: 25 fps source, stride 2
ROWS = 39                           # taps per window
WIDTHS = (1, 3, 7, 19, 39)          # pooling widths, in taps
H = ROWS // 2
RATIO = FPS125 / 2.0                # the head is trained on a 2 fps grid
TAPS = RATIO * np.arange(-H, H + 1)
EDGE = int(np.ceil(H * RATIO))      # rows at each end with no full window


class Trunk(nn.Module):
    def __init__(self, cin=368, hid=128, rows=ROWS, widths=WIDTHS):
        super().__init__()
        self.rows, self.widths, self.out_dim = rows, tuple(widths), hid * len(widths)
        self.conv = nn.Sequential(nn.Conv1d(cin, hid, 3, padding=1), nn.BatchNorm1d(hid), nn.ReLU())

    def forward(self, x):                                   # x: [N, cin, rows]
        g = self.conv(x)
        c = self.rows // 2
        return torch.cat([g[:, :, max(0, c - w // 2): min(self.rows, c + w // 2 + 1)].mean(2)
                          for w in self.widths], dim=1)


class Net(nn.Module):
    def __init__(self, n_classes, trunk):
        super().__init__()
        self.trunk = trunk
        self.head = nn.Sequential(nn.Linear(trunk.out_dim, 128), nn.ReLU(), nn.Dropout(0.3),
                                  nn.Linear(128, n_classes))

    def forward(self, x):
        return self.head(self.trunk(x))


def load_head(ckpt_path, device='cpu'):
    """Load a v9 head checkpoint. Returns (model, meta).

    The checkpoint is our own file, so full unpickling is used (it stores plain dicts and lists)."""
    ck = torch.load(ckpt_path, map_location=device, weights_only=False)
    net = Net(len(ck['classes']), Trunk(cin=ck['cin'], hid=ck.get('hid', 128),
                                        rows=ck.get('rows', ROWS),
                                        widths=tuple(ck.get('widths', WIDTHS)))).to(device)
    net.load_state_dict(ck['state_dict'])
    net.eval()
    return net, ck
