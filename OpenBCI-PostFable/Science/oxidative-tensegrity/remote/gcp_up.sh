#!/usr/bin/env bash
# Create (or reuse) a 32-vCPU VM on the ScienceClaw GCP lab account and start the cpu32 sweep on it.
#   remote/gcp_up.sh <ssh-private-key-file>
# Uses the separate gcloud configuration "scienceclaw" so other gcloud accounts on this Mac are untouched,
# and a dedicated throwaway SSH key (never gcloud's default key).
set -euo pipefail
cd "$(dirname "$0")/.."
KEY="$1"
export CLOUDSDK_ACTIVE_CONFIG_NAME=scienceclaw
PROJECT="${PROJECT:-$(gcloud projects list --format='value(projectId)' --limit=1)}"
ZONE="${ZONE:-us-central1-a}"
VM="${VM:-oxt-cpu32}"
TYPE="${TYPE:-e2-standard-32}"
gcloud config set project "$PROJECT" >/dev/null
gcloud services enable compute.googleapis.com >/dev/null
if ! gcloud compute instances describe "$VM" --zone "$ZONE" >/dev/null 2>&1; then
  gcloud compute instances create "$VM" --zone "$ZONE" --machine-type "$TYPE" \
    --image-family debian-12 --image-project debian-cloud --boot-disk-size 50GB \
    --metadata "ssh-keys=oxt:$(cat "$KEY.pub")" --no-service-account --no-scopes
fi
IP=$(gcloud compute instances describe "$VM" --zone "$ZONE" --format='value(networkInterfaces[0].accessConfigs[0].natIP)')
SSH="ssh -i $KEY -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=$KEY.known_hosts oxt@$IP"
for i in $(seq 1 30); do $SSH true 2>/dev/null && break; sleep 5; done
$SSH "sudo apt-get -qq update && sudo apt-get -qq install -y python3-venv rsync >/dev/null"
rsync -az --delete -e "ssh -i $KEY -o UserKnownHostsFile=$KEY.known_hosts" \
  --exclude results --exclude '__pycache__' --exclude 'results_*.log' ./ "oxt@$IP:oxt/"
$SSH "cd ~/oxt && nohup bash -lc 'python3 -m venv ~/v && . ~/v/bin/activate && pip install -q numpy==1.26.4 scipy==1.14.1 pandas==2.2.3 matplotlib==3.9.2 && pip install -q --no-deps torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu && pip install -q filelock typing-extensions sympy==1.13.1 networkx jinja2 fsspec && python run_sweep.py --profile cpu32 && python make_figures.py --results results/cpu32' > ~/oxt-run.log 2>&1 < /dev/null & echo started on \$(hostname) \$(nproc) cpus"
echo "host: oxt@$IP   log: $SSH tail -f oxt-run.log"
echo "pull: rsync -az -e 'ssh -i $KEY -o UserKnownHostsFile=$KEY.known_hosts' oxt@$IP:oxt/results/cpu32/ results/cpu32/"
