"""The v8 network: one convolution, pooled at several temporal widths, then a small classifier.

The trunk was pre-trained on 500 SoccerNet-v2 games (17 classes) and then frozen; the head was trained on the
ball-action classes. Architecture matches the training notebook exactly, so checkpoints load without remapping.
"""
import numpy as np
import torch
import torch.nn as nn


class Trunk(nn.Module):
    def __init__(self, cin=512, hid=128, rows=39, widths=(1, 3, 7, 19, 39)):
        super().__init__()
        self.rows, self.widths, self.out_dim = rows, tuple(widths), hid * len(widths)
        self.conv = nn.Sequential(nn.Conv1d(cin, hid, 3, padding=1), nn.BatchNorm1d(hid), nn.ReLU())

    def forward(self, x):                                   # x: [N, 512, rows]
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


def load_scorer(ckpt_path, device="cpu"):
    """Load a v8 checkpoint. Returns (score_fn, meta).

    score_fn maps a numpy batch [N, 512, rows] to sigmoid scores [N, n_classes] (numpy).
    The checkpoint is our own file, so full unpickling is used (it stores plain dicts and lists)."""
    ck = torch.load(ckpt_path, map_location=device, weights_only=False)
    trunk = Trunk(hid=ck["hid"], rows=ck["rows"], widths=ck["widths"])
    net = Net(len(ck["classes"]), trunk).to(device)
    net.load_state_dict(ck["state_dict"])
    net.eval()

    @torch.no_grad()
    def score_fn(batch):
        xb = torch.from_numpy(np.ascontiguousarray(batch, dtype=np.float32)).to(device)
        return torch.sigmoid(net(xb)).cpu().numpy()

    return score_fn, ck
