#!/usr/bin/env bash
# Run a ScienceClaw multi-agent collective (Gemini backend) against the model's predictions, isolated.
#   swarm/run_scienceclaw_swarm.sh <gemini-keyfile> [work-dir]
#
# Isolation (see SECURITY-REVIEW.md, ScienceClaw section): throwaway Docker container, only a work folder and the
# key file (read-only) mounted, capabilities dropped. ScienceClaw executes LLM-written shell commands, so nothing
# else of value may be inside. Every investigation is --dry-run, and Infinite points at a dead local port.
# All investigations share one ~/.scienceclaw inside the container, so ScienceClaw's ArtifactReactor lets the
# collectives react to each other's artifacts (its documented single-machine coordination).
set -euo pipefail
cd "$(dirname "$0")"
KEYFILE="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
WORK="${2:-$PWD/work}"
COMMIT="${SCIENCECLAW_COMMIT:-894598c}"
MODEL="${GEMINI_MODEL:-gemini-3.6-flash}"
mkdir -p "$WORK"
cp topics.txt "$WORK/topics.txt"
docker rm -f sclaw >/dev/null 2>&1 || true
docker run -d --name sclaw --cpus 4 --memory 6g --cap-drop ALL \
  --cap-add CHOWN --cap-add DAC_OVERRIDE --cap-add FOWNER --cap-add SETUID --cap-add SETGID \
  --security-opt no-new-privileges \
  -v "$WORK":/work -v "$KEYFILE":/run/gemini.key:ro \
  python:3.12.7-bookworm sleep infinity >/dev/null
docker exec sclaw bash -c "
set -e
git clone -q https://github.com/lamm-mit/scienceclaw.git /opt/scienceclaw
cd /opt/scienceclaw && git checkout -q $COMMIT && git log -1 --format='%H %cd' > /work/scienceclaw_commit.txt
python -m venv /opt/v && . /opt/v/bin/activate
pip install -q -r requirements.txt
pip freeze > /work/pip-freeze-initial.txt
"
docker exec -e LLM_BACKEND=gemini -e GEMINI_MODEL="$MODEL" -e GEMINI_REASONING_EFFORT=medium \
  -e INFINITE_API_BASE=http://127.0.0.1:9 sclaw bash -c '
set -u
export GEMINI_API_KEY="$(cat /run/gemini.key)"
. /opt/v/bin/activate
cd /opt/scienceclaw
i=0
while IFS= read -r topic; do
  [ -z "$topic" ] && continue
  i=$((i+1))
  ( python bin/scienceclaw-investigate "$topic" --community materials --dry-run -v > /work/investigation_$i.log 2>&1
    echo "exit $?" >> /work/investigation_$i.log ) &
  sleep 20   # stagger so later collectives can react to earlier artifacts
done < /work/topics.txt
wait
pip freeze > /work/pip-freeze-final.txt
cp -r ~/.scienceclaw /work/scienceclaw_home 2>/dev/null || true
'
echo "logs and artifacts in $WORK"
