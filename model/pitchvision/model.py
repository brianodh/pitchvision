"""Temporal Conv1D action spotter (206,028 parameters for 12 classes)."""
import torch.nn as nn


class TemporalActionSpotter(nn.Module):
    def __init__(self, in_channels=512, num_classes=12, hidden_dim=128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv1d(in_channels, hidden_dim, kernel_size=3, padding=1),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.AdaptiveAvgPool1d(1),      # averages over the window W -> W-independent weights
            nn.Flatten(),
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, num_classes))   # logits; apply sigmoid for probabilities

    def forward(self, x):                 # x: [B, 512, W]
        return self.net(x)
