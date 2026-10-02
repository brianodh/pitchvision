"""End-to-end check on SYNTHETIC data - needs no dataset and no GPU (about 1 minute on a CPU).

It builds small fake feature files, then runs the real pipeline through its command-line entry points:
    run_experiment.py  (boundary-masked pooling, training, evaluation on 3 matches, random floors)
    make_figures.py    (figures, tables, error diagnostics)
and checks the outputs. The numbers it produces are meaningless; it only proves the code runs.

Run:  python scripts/smoke_test.py
"""
import json
import os
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
from pitchvision.data import CLASSES, valid_window_indices

T, N_TRAIN, WS = 220, 4, (7, 15)


def fake_match(rng):
    Y = np.zeros((T, len(CLASSES)), np.float32)
    for c in range(len(CLASSES)):
        Y[rng.choice(T, 10, replace=False), c] = 1
    X = rng.random((T, 512)).astype(np.float32)
    X[:, :len(CLASSES)] += 2.0 * Y                       # weak signal so there is something to learn
    return X, Y


def run(cmd):
    print('$', ' '.join(os.path.basename(c) if os.path.exists(c) else c for c in cmd))
    done = subprocess.run(cmd, capture_output=True, text=True)
    if done.returncode != 0:
        print(done.stdout[-1500:]); print(done.stderr[-2500:])
        raise SystemExit('SMOKE TEST FAILED')
    return done.stdout


def main():
    rng = np.random.default_rng(0)
    with tempfile.TemporaryDirectory() as tmp:
        feats, out = os.path.join(tmp, 'features'), os.path.join(tmp, 'out')
        os.makedirs(feats)
        for name in [f't{i}' for i in range(N_TRAIN)] + ['e0', 'e1', 'e2']:
            X, Y = fake_match(rng)
            np.save(os.path.join(feats, f'{name}_X.npy'), X)
            np.save(os.path.join(feats, f'{name}_Y.npy'), Y)

        stdout = run([sys.executable, os.path.join(HERE, 'run_experiment.py'), '--features', feats, '--out', out,
                      '--train'] + [f't{i}' for i in range(N_TRAIN)] +
                     ['--eval', 'valid=e0', 'test=e1', 'test2=e2', '--windows'] + [str(w) for w in WS] +
                     ['--seeds', '0', '--epochs', '2'])
        print(stdout.strip().splitlines()[-1])

        res = json.load(open(os.path.join(out, 'results_v3.json')))
        gid = np.repeat(np.arange(N_TRAIN), T)
        for W in WS:
            run_ = res['main'][f'W{W}_s0']
            assert run_['n_train_windows'] == len(valid_window_indices(gid, W)) \
                == N_TRAIN * T - 2 * (W // 2) - (N_TRAIN - 1) * (W - 1), 'boundary masking is wrong'
            assert all(np.isfinite(run_['losses'])), 'non-finite training loss'
            for key in ('valid', 'test', 'test2'):
                for proto in ('A_avg', 'B_avg'):
                    assert 0.0 <= run_[key][proto] <= 1.0, (W, key, proto)
        for key in ('valid', 'test', 'test2'):
            assert 0.0 <= res['random_floor'][key]['A_avg'] <= 1.0
        assert os.path.exists(os.path.join(out, 'v3_ckpt_W7_seed0.pt')), 'checkpoint not written'

        run([sys.executable, os.path.join(HERE, 'make_figures.py'), '--results', out])
        figs = sorted(os.listdir(os.path.join(out, 'figures_v3')))
        assert len(figs) == 4, figs
        assert os.path.exists(os.path.join(out, 'analysis_v3.json'))
        print('figures written:', figs)
    print('\nSMOKE TEST PASSED - the full pipeline runs end to end on this machine.')


if __name__ == '__main__':
    main()
