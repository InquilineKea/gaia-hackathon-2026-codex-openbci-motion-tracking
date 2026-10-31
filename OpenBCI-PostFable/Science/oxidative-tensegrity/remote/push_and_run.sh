#!/usr/bin/env bash
# Copy this project to a hackathon VM over SSH and start a run there in the background (survives disconnects).
#   remote/push_and_run.sh brev <ssh-host>     # GPU: ALCHEMI (MACE-OFF + MACE-MP) then the gpu sweep
#   remote/push_and_run.sh gcp  <ssh-host>     # 32 vCPU: cpu32 sweep
# Pull results back:  rsync -az <ssh-host>:oxt/results/ results/
set -euo pipefail
cd "$(dirname "$0")/.."
kind="$1"; host="$2"
rsync -az --delete --exclude results --exclude '__pycache__' --exclude 'results_*.log' ./ "$host:oxt/"
case "$kind" in
  brev) cmd="cd ~/oxt && ALCHEMI_COMMIT=84fe8e8fb8fab54863eea8f138722c7ab434966a RUN_ALCHEMI=1 bash remote/gpu_run.sh" ;;
  gcp)  cmd="cd ~/oxt && python3 -m venv ~/oxt-venv && . ~/oxt-venv/bin/activate && pip install -q numpy==1.26.4 scipy==1.14.1 pandas==2.2.3 matplotlib==3.9.2 && pip install -q --no-deps torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu && pip install -q filelock typing-extensions sympy==1.13.1 networkx jinja2 fsspec && python run_sweep.py --profile cpu32 && python make_figures.py --results results/cpu32" ;;
  *) echo "kind must be brev or gcp" >&2; exit 2 ;;
esac
ssh "$host" "nohup bash -lc '$cmd' > ~/oxt-run.log 2>&1 < /dev/null & echo started on \$(hostname)"
echo "watch: ssh $host tail -f oxt-run.log"
