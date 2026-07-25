# EEG Neurofeedback (OpenBCI Cyton, adaptive posterior montage)

A small neurofeedback stack you can run with a primary Cyton channel pair plus
optional posterior electrodes — or with no hardware at all, against a synthetic
board, to see the whole pipeline work end to end.

| File | What it is |
|---|---|
| `eeg_server.py` | BrainFlow/direct-serial → WebSocket bridge. Preserves a primary pair, independently quality-gates optional Pz/right-posterior sites, computes Welch PSD features, and streams them as JSON. |
| `neurofeedback_aurora.html` | A living particle field that brightens/warms as your target band power rises, plus an audio channel whose pitch tracks how fast your brain is running. "Feel it." |
| `spectral_scope.html` | A live log-log spectrum with the fitted 1/f line, the alpha peak (PAF), and χ. "Understand it." |

One server drives both front-ends.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# No hardware — test everything:
python eeg_server.py --board synthetic

# Real Cyton:
python eeg_server.py --board cyton --serial-port COM3   # or /dev/ttyUSB0 (Linux), /dev/cu.usbserial-XXXX (macOS)

# Real Cyton + Daisy:
python eeg_server.py --board cyton-daisy --serial-port /dev/cu.usbserial-XXXX

# Direct serial fallback if BrainFlow cannot prepare an already-streaming board:
python eeg_server.py --board cyton-serial --serial-port /dev/cu.usbserial-XXXX --channels 1 6

# Current four-input montage: channels 2 + 7, N5P at Pz, and N4P near P4/O2:
python eeg_server.py --board cyton-serial \
  --serial-port /dev/cu.usbserial-XXXX \
  --channels 1 6 --pz-channel 4 --posterior-right-channel 3
```

Common flags: `--band alpha|beta` (alpha is the easiest first target),
`--channels 0 1`, `--pz-channel`, `--posterior-right-channel`,
`--line 60|50`, `--window 4`, `--port 8765`. Channel arguments are zero-based,
so N4P is `3` and N5P is `4`.

### Viewing a front-end against live data

Browsers block insecure `ws://` from an `https://` page, so **run the HTML locally**:

```bash
python -m http.server 8000
# open http://localhost:8000/neurofeedback_aurora.html
```

Both HTML files are already connected to `ws://localhost:8765` and automatically
retry if the bridge starts after the page.

## First thing to do with real electrodes

**The alpha-blocking test.** Close your eyes — occipital alpha should surge; open
them — it craters. If the field swells and collapses with your eyelids, the entire
chain is working. If not, it's a montage/impedance problem, and no downstream
tuning will help. Put electrodes at O1/O2 or Pz (referenced to a mastoid/earlobe)
for the strongest alpha.

## Feedback with your eyes closed

Your strongest alpha appears with your eyes **closed**, which is exactly when you
cannot watch the aurora. So the field also has a voice: press **A** (or the Audio
button) and you get a tone whose **pitch rises when your brain runs faster and falls
when it runs slower**.

- **Pitch: PAF** (default) maps your peak alpha frequency straight onto pitch — 10 Hz
  sits at A3, and 0.1 Hz is roughly half a semitone, so a real alpha slowdown is
  plainly audible.
- **Pitch: speed** uses the broadband spectral centroid instead (always defined, even
  when there is no clean alpha peak), read as a deviation from your own session
  baseline. **Pitch: β/α** does the same for beta dominance.
- **Tone: scale** snaps to a pentatonic scale if a continuous glissando gets tiring;
  **glide** is the continuous version.
- A quiet fifth swells on top when your band reward is above baseline, and a clenched
  jaw ducks the volume and *freezes* the pitch rather than letting muscle sound like a
  brain state.

Hit **Calibrate** (or **C**) while resting to set the baseline the relative sources
compare against.

## A note on what this is (and isn't)

It's a *mirror* — a real-time view of your own signal — not a medical device or a
training program. Neurofeedback's ability to durably *train* the brain is genuinely
contested; a live window on your oscillations is real regardless of that debate.
Two of the design choices worth knowing: band power is normalized to your own
recent baseline (absolute values are meaningless across sessions), and PAF is read
*after* removing the 1/f background (the modern FOOOF/specparam approach), because
a naive peak drifts when the spectral tilt changes even if alpha doesn't move.

The Aurora's posterior vigilance/drowsiness/on-task values are exploratory
within-session proxies, not diagnoses or literal detectors of thoughts. Each
posterior lead must independently pass amplitude, mains, and high-frequency
artifact checks. If only one posterior site is clean, it can drive the posterior
features alone; if neither is clean, posterior reward remains neutral and the
primary pair continues.

Deeper rationale, the known version traps, and the open TODO list live in
**`AGENTS.md`** (which Codex CLI and Claude Code both read automatically).

## Requirements

Python 3.9+, and `brainflow numpy scipy websockets` (see `requirements.txt`).
For a real board you'll also need the Cyton + USB dongle and its serial port.
