"""ResNet-18 (ImageNet) frame features at 1 frame per second."""
import time
import cv2
import numpy as np
import torch
import torchvision.models as models
import torchvision.transforms as T


def load_backbone(device):
    bb = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
    bb.fc = torch.nn.Identity()                       # 512-d output
    tf = T.Compose([T.ToPILImage(), T.Resize((224, 224)), T.ToTensor(),
                    T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])
    return bb.to(device).eval(), tf


def extract_video(video_path, backbone, tf, device, max_seconds=None, batch=64):
    """Read the video sequentially and embed the first frame of every second
    (frame index % round(fps) == 0). Returns ([T, 512] float32, fps, seconds_taken)."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    step = int(round(fps))
    t0, buf, out, idx, kept = time.time(), [], [], 0, 0

    def flush():
        with torch.no_grad():
            out.append(backbone(torch.stack(buf).to(device)).cpu().numpy())
        buf.clear()

    while (max_seconds is None or kept < max_seconds) and cap.grab():
        if idx % step == 0:
            _, fr = cap.retrieve()
            buf.append(tf(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)))
            kept += 1
            if len(buf) == batch:
                flush()
        idx += 1
    if buf:
        flush()
    cap.release()
    return np.vstack(out).astype(np.float32), fps, time.time() - t0
