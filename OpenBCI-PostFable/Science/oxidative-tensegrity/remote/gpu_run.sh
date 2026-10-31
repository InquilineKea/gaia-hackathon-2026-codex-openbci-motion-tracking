#!/usr/bin/env bash
# Run on a disposable CUDA box (Brev instance or Nebius VM/job). Never on the personal Mac.
#   bash remote/gpu_run.sh                  # mesoscale sweep only (torch/scipy/pandas, pinned)
#   ALCHEMI_COMMIT=<reviewed sha> RUN_ALCHEMI=1 bash remote/gpu_run.sh   # + atomistic crosslink stage
# Outputs: results/gpu/ and results/crosslink_params.json.  Copy them back yourself.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="${OUT:-results/gpu}"
VENV="${VENV:-/tmp/oxt-venv}"

nvidia-smi --query-gpu=name,memory.total --format=csv

# --- mesoscale: only well-established packages, exact versions (all published > 1 year ago) ---------
python3 -m venv "$VENV"
. "$VENV/bin/activate"
python -m pip install --upgrade "pip==24.3.1"
python -m pip install "numpy==1.26.4" "scipy==1.14.1" "pandas==2.2.3" "matplotlib==3.9.2"
python -m pip install "torch==2.5.1" --index-url https://download.pytorch.org/whl/cu124
python - <<'EOF'
import torch; print("torch", torch.__version__, "cuda", torch.cuda.is_available(), torch.cuda.get_device_name(0))
EOF

# if the ALCHEMI stage already produced crosslink rigidities, the network sweep uses them
if [[ "${RUN_ALCHEMI:-0}" == "1" ]]; then
  : "${ALCHEMI_COMMIT:?set ALCHEMI_COMMIT to the commit sha you reviewed (see SECURITY-REVIEW.md)}"
  python3 -m venv /tmp/alchemi-venv
  . /tmp/alchemi-venv/bin/activate
  python -m pip install --upgrade "pip==24.3.1" "uv==0.5.11"
  # first-index strategy: never let an extra index shadow a PyPI name (upstream default is unsafe-best-match)
  uv pip install --index-strategy first-index \
      "nvalchemi-toolkit[cu13,mace] @ git+https://github.com/NVIDIA/nvalchemi-toolkit@${ALCHEMI_COMMIT}" \
      "rdkit==2024.9.6" "ase==3.24.0" \
      --extra-index-url https://download.pytorch.org/whl/cu130 --extra-index-url https://pypi.nvidia.com
  python alchemi_crosslinks.py --model mace-off:medium --device cuda
  python alchemi_crosslinks.py --model mace-mp:medium-0b2 --device cuda --out results/crosslink_params_mp.json
  deactivate
  . "$VENV/bin/activate"
fi

python run_sweep.py --profile gpu --device cuda --out "$OUT"
python make_figures.py --results "$OUT"
echo "done: $OUT"
