#!/usr/bin/env bash
# Submit the GPU sweep as a Nebius serverless AI job on the ScienceClaw tenant (Nebius-Academy-8dj).
# Prerequisites (you do these; nothing here reads or stores credentials):
#   1. accept the tenant invite, install + `nebius profile create` the CLI yourself
#   2. create a storage bucket for outputs and put its id in NEBIUS_BUCKET
#   3. export NEBIUS_SUBNET=<vpcsubnet-...> from the tenant
# Flags follow docs.nebius.com/serverless/jobs/manage and the VM types page (checked 2026-10-30).
# The event asks for 1 GPU per team: keep --preset 1gpu-16vcpu-200gb.
set -euo pipefail
cd "$(dirname "$0")/.."
: "${NEBIUS_BUCKET:?storage bucket id for results}"
: "${NEBIUS_SUBNET:?vpc subnet id}"

tar czf /tmp/oxt-code.tgz --exclude results --exclude '__pycache__' oxt run_sweep.py make_figures.py \
    alchemi_crosslinks.py remote README.md
ls -lh /tmp/oxt-code.tgz

nebius ai job create \
  --name oxt-sweep-$(date +%H%M) \
  --image pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime \
  --container-command bash \
  --args "-c 'mkdir -p /workspace/oxt && cd /workspace/oxt && tar xzf /workspace/oxt-code.tgz && pip install numpy==1.26.4 scipy==1.14.1 pandas==2.2.3 matplotlib==3.9.2 && python run_sweep.py --profile gpu --device cuda --out /output/gpu && python make_figures.py --results /output/gpu'" \
  --platform gpu-h100-sxm \
  --preset 1gpu-16vcpu-200gb \
  --timeout 6h \
  --inject-file "/tmp/oxt-code.tgz:/workspace/oxt-code.tgz" \
  --volume "${NEBIUS_BUCKET}:/output:rw" \
  --subnet-id "${NEBIUS_SUBNET}"

echo "follow with: nebius ai job list ; nebius ai job logs <job_ID> --follow"
