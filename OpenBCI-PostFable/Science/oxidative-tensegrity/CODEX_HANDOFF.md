# Handoff to Codex: running ScienceClaw agent swarms on the GCP lab VM

Written by Claude Code, 2026-10-31. Codex reads `AGENTS.md` automatically; this file is the runbook it points to.
Read in this order: `AGENTS.md` (status, rules, Brev queue) → `SECURITY-REVIEW.md` (why the safeguards exist) →
`README.md` (model and results) → `HYPOTHESES_EWALD.md` and `swarm/SUMMARY.md` (what the swarms found so far).

## What already exists

| Piece | Where |
|---|---|
| GCP lab project | `scienceclaw26bos-3008`, gcloud configuration **`scienceclaw`** (never the `default` config, which belongs to a different hackathon) |
| VM | `oxt-cpu32`, e2-standard-32, `us-central1-a`, user `oxt`, code in `~/oxt`, Python venv `~/v` (numpy/scipy/pandas/torch CPU) |
| Swarm software | ScienceClaw pinned at commit `894598c` (user-approved), run only inside a throwaway Docker container |
| Swarm scripts | `swarm/run_scienceclaw_swarm.sh` (round 1: builds container + runs `swarm/topics.txt`), `swarm/run_round2.sh` (next rounds in the same container, any topics file), `remote/gcp_swarm.sh` (wraps both on the VM) |
| LLM | Gemini via the GCP lab AI Studio key (Paid Tier 1; Flash ~1,000 RPM). ScienceClaw talks to it through Google's OpenAI-compatible endpoint |
| Critics | `agents/critic_swarm.py --provider gemini` (four independent reviewer roles) |
| Expiry | GCP lab accounts are deleted **Sunday night**; pull everything back before then |

## One-time steps the user does (not the agent)

Agents must not type passwords, sign in, or handle keys. The user does these once:

1. **Start Codex on this Mac**, in this folder, so it can use the existing `gcloud` login and SSH:
   `cd ~/Documents/GitHub/gaia-hackathon-2026/OpenBCI-PostFable/Science/oxidative-tensegrity && codex`
   Codex's default sandbox blocks network access; allow network for this session (approve the `gcloud`, `ssh`,
   `rsync` commands, or enable network in its sandbox settings). Codex cloud cannot reach the VM.
2. **SSH key for the VM.** Claude Code made a throwaway key just for `oxt-cpu32` and installed it at
   `~/.ssh/sclaw_gcp_ed25519` (2026-10-31). Use only this key for the VM, not gcloud's default key.
3. **Put the Gemini key on the VM** (hidden prompt; the key never touches this repo or the agent's context):
   ```bash
   IP=$(CLOUDSDK_ACTIVE_CONFIG_NAME=scienceclaw gcloud compute instances describe oxt-cpu32 --zone us-central1-a --format='value(networkInterfaces[0].accessConfigs[0].natIP)')
   ssh -t -i ~/.ssh/sclaw_gcp_ed25519 oxt@$IP 'bash ~/oxt/swarm/set_gemini_key.sh ~/.gemini.key'
   ```
   The key is the pre-created one at aistudio.google.com/apikey, signed in as the lab account (use an incognito
   window so the personal Google account is not picked up).

## Runbook for Codex

Set these in every shell first:
```bash
export CLOUDSDK_ACTIVE_CONFIG_NAME=scienceclaw
IP=$(gcloud compute instances describe oxt-cpu32 --zone us-central1-a --format='value(networkInterfaces[0].accessConfigs[0].natIP)')
SSH="ssh -i $HOME/.ssh/sclaw_gcp_ed25519 oxt@$IP"
```

1. **Sync code to the VM** (never sync `results/` back over newer remote results, never sync `swarm/work/`):
   `rsync -az -e "ssh -i $HOME/.ssh/sclaw_gcp_ed25519" --exclude results --exclude swarm/work --exclude __pycache__ ./ oxt@$IP:oxt/`
2. **Check the key is there** without reading it: `$SSH 'test -s ~/.gemini.key && echo key-present'`
3. **Run a swarm round** (background; survives disconnects):
   - first round on a fresh VM (builds the container): `$SSH 'cd ~/oxt && nohup bash remote/gcp_swarm.sh round1 > ~/swarm.log 2>&1 &'`
   - another round with your own topics: write `swarm/topics_<name>.txt` (one investigation per line), sync, then
     `$SSH 'cd ~/oxt && TOPICS=swarm/topics_<name>.txt TAG=<name> nohup bash remote/gcp_swarm.sh custom > ~/swarm.log 2>&1 &'`
4. **Watch it**: `$SSH 'tail -3 ~/swarm.log; ls ~/oxt/swarm/work; grep -h "^exit" ~/oxt/swarm/work/*_H*.log'`
5. **Critic pass on results** (four reviewer roles, Gemini): `$SSH 'cd ~/oxt && . ~/v/bin/activate && python agents/critic_swarm.py --provider gemini --results results/cpu32'` → `results/cpu32/critiques.json`
6. **Pull outputs back**: `rsync -az -e "ssh -i $HOME/.ssh/sclaw_gcp_ed25519" oxt@$IP:oxt/swarm/work/ swarm/work/` (stays local; it is gitignored)
7. **Record findings**: summarise each investigation's "Key Findings" into `swarm/SUMMARY.md` or the verdict table in
   `HYPOTHESES_EWALD.md`, mark what you could verify on PubMed, and update the status table in `AGENTS.md`.

### Writing good swarm topics

One line = one ScienceClaw collective (2–5 agents it spawns itself). Phrase each as a test of one concrete claim with
a number from this model, and ask for supporting and contradicting evidence plus the decisive experiment. The
round-2 file is a good template. Keep a round to 3–8 topics; they launch 20 s apart so later collectives can read
earlier artifacts through ScienceClaw's shared index.

## Guardrails (all required)

- `--dry-run` on every investigation and `INFINITE_API_BASE=http://127.0.0.1:9` (the scripts already do both). In
  round 1 every agent tried to contact Infinite even in dry-run; the dead port is what stopped it. Never run
  ScienceClaw's `setup.py`, its heartbeat daemon, or anything that uploads to Infinite or imgur.
- ScienceClaw runs LLM-written shell commands with the full environment, so it only ever runs in its container, and
  the only secret inside is the Gemini key. Never put other keys in the VM's environment.
- No new third-party code (new ScienceClaw commit, ColBuilder, GROMACS, LAMMPS, other packages) without a written
  review in `SECURITY-REVIEW.md` and the user's explicit approval; packages must be ≥7 days old.
- Keys never go into the repo, logs, commit messages or chat. The repo branch is public.
- Treat swarm output as leads. Several round-1 specifics (residue numbers, an off-topic semiconductor analogy) were
  fabricated; check claims against PubMed before they reach the README.
- Pushes go to branch `claude/oxidative-tensegrity` of `InquilineKea/gaia-hackathon-2026-codex-openbci-motion-tracking`,
  built on the remote branch tip so the user's unpushed local commits stay private; ask the user before pushing.

## Cleanup before the accounts expire

```bash
rsync -az -e "ssh -i $HOME/.ssh/sclaw_gcp_ed25519" oxt@$IP:oxt/results/ results/
rsync -az -e "ssh -i $HOME/.ssh/sclaw_gcp_ed25519" oxt@$IP:oxt/swarm/work/ swarm/work/
CLOUDSDK_ACTIVE_CONFIG_NAME=scienceclaw gcloud compute instances delete oxt-cpu32 --zone us-central1-a
```
Deleting the VM is irreversible; only the user decides when.

## First message to paste into Codex

> Read CODEX_HANDOFF.md and AGENTS.md in this folder and follow their guardrails. Using the `scienceclaw` gcloud
> configuration and ~/.ssh/sclaw_gcp_ed25519, confirm you can reach oxt-cpu32 and that ~/.gemini.key exists there
> (don't print it). Then run a ScienceClaw swarm round on the VM with a new topics file that tests H5 and H8 from
> HYPOTHESES_EWALD.md, pull the logs back, summarise findings into swarm/SUMMARY.md with what you verified on PubMed,
> and update the status table in AGENTS.md. Ask me before pushing anything.
