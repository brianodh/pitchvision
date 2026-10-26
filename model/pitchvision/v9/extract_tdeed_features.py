#!/usr/bin/env python3
"""Capture T-DEED's temporal encoder output -- the tensor its final classifier reads -- as a
reusable [T, 368] feature array per match, for a downstream model of our own.

Run from inside a checkout of https://github.com/arturxe2/T-DEED (GPL-3.0); this file imports
that project's modules and is therefore GPL-3.0 too.

    python extract_features_v8.py --model SoccerNetBall_test \
        --video_path match.mp4 --out_path feats_match.npy
"""
import argparse
import os

import numpy as np
import torch
from torch.utils.data import DataLoader

from util.io import load_json
from model.model import TDEEDModel
from dataset.frame import ActionSpotInferenceDataset
from util.dataset import load_classes

STRIDE_SNB = 2          # T-DEED's own stride for the soccernetball dataset


def get_args():
    p = argparse.ArgumentParser()
    p.add_argument('--model', required=True)
    p.add_argument('--video_path', required=True)
    p.add_argument('--out_path', required=True)
    p.add_argument('--frame_width', type=int, default=796)
    p.add_argument('--frame_height', type=int, default=448)
    return p.parse_args()


def update_args(args, config):
    for k in ['frame_dir', 'store_dir', 'store_mode', 'batch_size', 'clip_len', 'dataset',
              'radi_displacement', 'epoch_num_frames', 'feature_arch', 'learning_rate', 'mixup',
              'modality', 'num_classes', 'num_epochs', 'warm_up_epochs', 'start_val_epoch',
              'temporal_arch', 'n_layers', 'sgp_ks', 'sgp_r', 'only_test', 'criterion',
              'num_workers']:
        setattr(args, k, config[k])
    args.save_dir = config['save_dir'] + '/' + args.model
    args.crop_dim = config['crop_dim'] if config['crop_dim'] > 0 else None
    args.pretrain = config.get('pretrain', None)
    return args


def main(args):
    config = load_json(os.path.join('config', args.model.split('_')[0] + '/' + args.model + '.json'))
    args = update_args(args, config)

    classes = load_classes(os.path.join('data', args.dataset, 'class.txt'))
    model = TDEEDModel(args=args)
    if args.pretrain is not None:
        pretrain_classes = load_classes(os.path.join('data', args.pretrain['dataset'], 'class.txt'))
        n_classes = [len(classes) + 1, len(pretrain_classes) + 1]
        model._model.update_pred_head(n_classes)
        model._num_classes = np.array(n_classes).sum()
    model.load(torch.load(os.path.join(
        os.getcwd(), 'checkpoints', args.model.split('_')[0], args.model, 'checkpoint_best.pt')))

    # The representation we want is the input to the final classifier.
    captured = {}

    def _hook(mod, inp):
        captured['feat'] = inp[0].detach().float().cpu().numpy()   # [batch, clip_len, feat_dim]

    model._model._pred_fine.register_forward_pre_hook(_hook)

    stride = STRIDE_SNB
    ds = ActionSpotInferenceDataset(
        args.video_path, clip_len=args.clip_len, overlap_len=args.clip_len // 4 * 3,
        stride=stride, dataset=args.dataset, size=(args.frame_width, args.frame_height))
    assert ds._video_len > 0, f'cv2 reported 0 frames for {args.video_path} -- missing or unreadable'
    loader = DataLoader(ds, batch_size=args.batch_size, shuffle=False,
                        num_workers=args.num_workers, pin_memory=True, drop_last=False)

    n_rows = ds._video_len // stride
    feat_dim, features_sum = None, None
    support = np.zeros(n_rows, np.int32)

    # Clips overlap; accumulate and average, mirroring util.eval.inference().
    for frames, starts in loader:
        _, _ = model.predict(frames)
        batch_feat = captured['feat']
        if feat_dim is None:
            feat_dim = batch_feat.shape[-1]
            features_sum = np.zeros((n_rows, feat_dim), np.float32)
            print('feat_dim:', feat_dim)
        for i in range(frames.shape[0]):
            feat = batch_feat[i]
            start = starts[i].item()
            if start < 0:
                feat = feat[-start:, :]
                start = 0
            end = min(start + feat.shape[0], n_rows)
            feat = feat[:end - start, :]
            features_sum[start:end, :] += feat
            support[start:end] += 1

    features = features_sum / np.maximum(support, 1)[:, None]
    np.save(args.out_path, features)
    print('saved', args.out_path, features.shape)


if __name__ == '__main__':
    main(get_args())
