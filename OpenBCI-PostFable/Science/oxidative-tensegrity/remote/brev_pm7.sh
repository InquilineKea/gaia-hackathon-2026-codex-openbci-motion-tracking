#!/usr/bin/env bash
# PM7 (MOPAC) tie-breaker for the crosslink stretch scan, on the Brev box, CPU only.
# Runs inside python:3.12 with networking off; reuses the rdkit/ase in the oxt-alchemi-venv volume (read-only).
# The MOPAC tarball is copied in beforehand and checked against GitHub's published digest.
#   cd ~/oxt && PM7_ARGS="--only disulfide --n-strain 3" bash remote/brev_pm7.sh     # smoke test
#   cd ~/oxt && setsid nohup bash remote/brev_pm7.sh > ~/oxt-pm7.log 2>&1 < /dev/null &
set -euo pipefail
cd "$(dirname "$0")/.."
MOPAC_TGZ="${MOPAC_TGZ:-$HOME/mopac-23.2.5-linux.tar.gz}"
MOPAC_SHA=bc1a814aaf58451ab743efedd967a3ed3b26f61689f562dcc9339a5c4b1a9377   # openmopac v23.2.5, reviewed 2026-10-31
if [ -z "${IN_CONTAINER:-}" ]; then
  echo "$MOPAC_SHA  $MOPAC_TGZ" | sha256sum -c -
  exec docker run --rm --network none -e IN_CONTAINER=1 -e PM7_ARGS="${PM7_ARGS:-}" -v "$PWD":/work -w /work \
    -v "$MOPAC_TGZ":/opt/mopac.tgz:ro -v oxt-alchemi-venv:/root/alchemi-venv:ro \
    python:3.12.7-bookworm bash remote/brev_pm7.sh
fi
mkdir -p /opt/mopac && tar xzf /opt/mopac.tgz -C /opt/mopac --strip-components=1
export PATH=/opt/mopac/bin:$PATH LD_LIBRARY_PATH=/opt/mopac/lib OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
. ~/alchemi-venv/bin/activate
# shellcheck disable=SC2086
python -W ignore pm7_crosslinks.py --workers "$(nproc --all)" ${PM7_ARGS:---seeds 7,11,23 --out results/alchemi_brev/crosslink_pm7.json}
echo "ALL DONE"
