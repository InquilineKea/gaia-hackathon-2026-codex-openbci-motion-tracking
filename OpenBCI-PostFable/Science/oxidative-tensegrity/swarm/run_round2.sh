#!/usr/bin/env bash
# Second ScienceClaw round in the SAME isolated container as round 1, so ~/.scienceclaw artifacts from round 1 stay
# visible to the ArtifactReactor. Same safeguards: --dry-run, Infinite pointed at a dead port.
#   swarm/run_round2.sh [work-dir]
set -euo pipefail
cd "$(dirname "$0")"
WORK="${1:-$PWD/work}"
MODEL="${GEMINI_MODEL:-gemini-3.6-flash}"
docker ps --filter name=sclaw --format '{{.Names}}' | grep -qx sclaw || { echo "container sclaw not running; run run_scienceclaw_swarm.sh first" >&2; exit 1; }
cp topics_round2.txt "$WORK/topics_round2.txt"
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
  ( python bin/scienceclaw-investigate "$topic" --community biology --dry-run -v > /work/round2_H$i.log 2>&1
    echo "exit $?" >> /work/round2_H$i.log ) &
  sleep 20
done < /work/topics_round2.txt
wait
pip freeze > /work/pip-freeze-round2.txt
rm -rf /work/scienceclaw_home && cp -r ~/.scienceclaw /work/scienceclaw_home 2>/dev/null || true
'
echo "round 2 logs in $WORK/round2_H*.log"
