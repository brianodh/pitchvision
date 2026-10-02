"""Training and inference for the temporal Conv1D spotter (PyTorch)."""
import random
import time

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader

from .data import WindowDataset
from .model import TemporalActionSpotter

# Hyper-parameters held constant across every experimental condition.
BATCH, LR, WEIGHT_DECAY, POS_WEIGHT, EPOCHS = 64, 1e-3, 1e-4, 15.0, 12


def set_seed(seed):
    """Seed every RNG and force deterministic cuDNN (needed for bit-exact reproduction)."""
    random.seed(seed); np.random.seed(seed)
    torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def _sync(device):
    if device == 'cuda':
        torch.cuda.synchronize()


def train_model(X, Y, centres, W, seed, device, num_classes=12, epochs=EPOCHS):
    """Train one model. Returns (model, per-epoch mean loss, wall-clock training seconds).

    Loss: BCEWithLogitsLoss with pos_weight = 15 on every class, i.e. event seconds are weighted 15x
    because they are heavily outnumbered by background seconds."""
    set_seed(seed)                      # re-seeded before EVERY run (not once per script)
    loader = DataLoader(WindowDataset(X, Y, centres, W), batch_size=BATCH, shuffle=True)
    model = TemporalActionSpotter(num_classes=num_classes).to(device)
    criterion = nn.BCEWithLogitsLoss(pos_weight=torch.full((num_classes,), POS_WEIGHT, device=device))
    optimiser = optim.Adam(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    losses = []
    _sync(device); t0 = time.time()
    for _ in range(epochs):
        model.train(); running = 0.0
        for xb, yb in loader:
            xb, yb = xb.to(device), yb.to(device)
            optimiser.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward(); optimiser.step()
            running += loss.item() * len(xb)
        losses.append(running / len(loader.dataset))
    _sync(device)
    return model, losses, time.time() - t0


def predict(model, X, Y, centres, W, device):
    """Sigmoid probabilities for each centre second. Returns (P [N, C], inference seconds)."""
    loader = DataLoader(WindowDataset(X, Y, centres, W), batch_size=BATCH, shuffle=False)
    model.eval(); out = []
    _sync(device); t0 = time.time()
    with torch.no_grad():
        for xb, _ in loader:
            out.append(torch.sigmoid(model(xb.to(device))).cpu().numpy())
    _sync(device)
    return np.vstack(out), time.time() - t0
