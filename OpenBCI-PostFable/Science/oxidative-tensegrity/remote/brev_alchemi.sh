#!/usr/bin/env bash
# ALCHEMI jobs on a Brev GPU instance (B1 converged crosslink scan with two MLIPs, B5 collagen-GAG interface).
# Runs from ~/oxt on the instance; outputs in ~/oxt/results/. Log: ~/oxt-alchemi.log
#   brev copy <tarball> <instance>:~/  then:  brev exec <instance> "cd ~/oxt && nohup bash remote/brev_alchemi.sh > ~/oxt-alchemi.log 2>&1 &"
set -euo pipefail
cd "$(dirname "$0")/.."
COMMIT=84fe8e8fb8fab54863eea8f138722c7ab434966a   # user-approved 2026-10-30
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv
# ALCHEMI and aimnet need Python >= 3.11; the Brev image has 3.10, so run inside python:3.12 with the GPU via CDI
if [ -z "${IN_CONTAINER:-}" ]; then
  exec docker run --rm --device nvidia.com/gpu=all -e IN_CONTAINER=1 -v "$PWD":/work -w /work \
    -v oxt-alchemi-venv:/root/alchemi-venv -v oxt-cache:/root/.cache python:3.12.7-bookworm bash remote/brev_alchemi.sh
fi
if [ ! -x ~/alchemi-venv/bin/python ]; then
  python3 -m venv ~/alchemi-venv
  ~/alchemi-venv/bin/pip install -q "pip==24.3.1" "uv==0.5.11"
  # PyPI only: no extra indexes, so nothing can shadow a PyPI name (upstream pyproject uses unsafe-best-match;
  # uv also ranks extra indexes above PyPI, which picked a stale requests from the PyTorch index).
  # PyPI's Linux x86-64 torch wheels are CUDA builds, which is all the cu13 extra needs here.
  ~/alchemi-venv/bin/uv pip install --python ~/alchemi-venv/bin/python \
    "nvalchemi-toolkit[cu13,mace] @ git+https://github.com/NVIDIA/nvalchemi-toolkit@${COMMIT}" \
    "aimnet==0.2.5" "rdkit==2024.9.6" "ase==3.24.0"
  ~/alchemi-venv/bin/uv pip freeze --python ~/alchemi-venv/bin/python > results/brev-alchemi-freeze.txt
fi
. ~/alchemi-venv/bin/activate
python -c "import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available(), torch.cuda.get_device_name(0))"
mkdir -p results/alchemi_gag
echo "=== B5 collagen-GAG (AIMNet2), 24 orientations"
[ -s results/alchemi_gag/collagen_gag.json ] || python -W ignore alchemi_collagen_gag.py --device cuda --orient 24 --out results/alchemi_gag/collagen_gag.json
echo "=== B1a crosslink scan, MACE-OFF medium"
python -W ignore alchemi_crosslinks.py --model mace-off:medium --device cuda --steps 3000 --fmax 0.02 --chem-per-batch 2 \
  --out results/crosslink_params.json
echo "=== B1b crosslink scan, MACE-MP medium-0b2 (independent model family)"
python -W ignore alchemi_crosslinks.py --model mace-mp:medium-0b2 --device cuda --steps 3000 --fmax 0.02 --chem-per-batch 2 \
  --out results/crosslink_params_mp.json
echo "ALL DONE"
