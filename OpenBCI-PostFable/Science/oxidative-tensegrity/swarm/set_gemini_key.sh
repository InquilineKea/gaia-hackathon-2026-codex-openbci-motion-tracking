#!/usr/bin/env bash
# Type the ScienceClaw lab Gemini key (aistudio.google.com/apikey, signed in as the lab account).
# It is stored outside the repo with owner-only permissions and mounted read-only into the swarm container.
set -euo pipefail
KEYFILE="${1:?usage: set_gemini_key.sh <keyfile>}"
read -rs -p "Gemini API key (input hidden): " K
echo
[ -n "$K" ] || { echo "empty key, nothing saved" >&2; exit 1; }
umask 077
printf %s "$K" > "$KEYFILE"
unset K
echo "saved to $KEYFILE ($(wc -c < "$KEYFILE" | tr -d ' ') chars)"
