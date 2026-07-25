# EEG Neurofeedback — agent context

A DIY neurofeedback stack for an OpenBCI Cyton primary pair plus optional
posterior electrodes. Three parts:

- `eeg_server.py` — Python bridge. Reads the Cyton via **BrainFlow**, filters,
  computes a Welch PSD (**scipy**), derives features (**numpy**), streams JSON over
  a **WebSocket**. Runs against a synthetic board with no hardware for testing.
- `neurofeedback_aurora.html` — a living particle field whose intensity/warmth
  tracks a normalized band-power reward. The "feel it" front-end.
- `spectral_scope.html` — a live log-log PSD with the fitted 1/f line overlaid,
  the alpha peak (PAF) marked, and the aperiodic exponent χ read out. The
  "understand it" front-end.

One server drives both: it emits `band/emg/ch1/ch2`, artifact-gated
`posterior/posterior_sites` features (for the field), and
`paf/chi/freqs/logpsd` (for the scope) in every message.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python eeg_server.py --board synthetic                # no hardware, full pipeline
python eeg_server.py --board cyton --serial-port COM3 # real (or /dev/ttyUSB0, /dev/cu.usbserial-XXXX)
python eeg_server.py --board cyton-serial --serial-port /dev/cu.usbserial-XXXX \
  --channels 1 6 --pz-channel 4 --posterior-right-channel 3
```

To view a front-end **against real data**, serve the HTML locally (see the
mixed-content trap below) and uncomment the WebSocket seam at the bottom of
`eeg_server.py` — it has paste-in snippets for both HTML files.

```bash
python -m http.server 8000     # then open http://localhost:8000/neurofeedback_aurora.html
```

## Design decisions — do NOT silently undo these

- **Measure vs. train are different goals.** This is built as a *mirror/toy*, not
  therapy. Neurofeedback's training efficacy is contested (sham-controlled trials
  attribute much to placebo); a real-time window on your own signal is real
  regardless. Keep that framing.
- **Absolute band power is meaningless across sessions** (impedance, skull,
  montage). `RunningNorm` maps each value to the subject's own recent
  distribution (robust z → logistic → 0..1). That's why the field's drive is
  relative, not absolute. Don't replace it with a hardcoded gain.
- **PAF is computed on the 1/f-REMOVED residual, not raw power.** Naive argmax in
  the alpha window is biased by the aperiodic slope — a steeper 1/f drags the
  "peak" toward the low-frequency edge even when alpha didn't move. This is the
  whole point of FOOOF/specparam (Donoghue 2020). The scope has a raw-vs-removed
  toggle that demonstrates the bias live; keep both so the difference stays visible.
- **χ (aperiodic exponent) has NO fixed valence.** Flatter (smaller χ) = more
  excitation / more awake — but also the aging "neural noise" signature. Steeper =
  more inhibition — but also reads "cleaner/younger." So the scope lets the user
  pick reward = PAF↑ / flatter / steeper and watch the sign flip. Do not hardcode
  "higher/lower is better." PAF↑ is the one direction with a stable meaning.
- **The time/resolution tradeoff is deliberate and OPPOSITE for the two feature
  families.** Band power → fast updates wanted → short window → coarse frequency
  resolution. PAF/χ → slow, trait-ish signals → long window (4 s) fine → good
  resolution for free. That's why `--window 4`.
- **The audio channel is the eyes-closed path, and it has its own rules.** Pitch
  carries "how fast the brain is running"; the aurora's colour/motion cannot be seen
  by the person who is generating the strongest alpha. Three invariants: (a) the tone
  is driven by a `setInterval`, NOT `requestAnimationFrame` — rAF stops dead in a
  hidden tab and a frozen tone is the one failure an eyes-closed user cannot notice;
  (b) EMG ducks the volume AND freezes the pitch, because a jaw clench must never
  sound like a state change; (c) PAF is mapped ABSOLUTELY (10 Hz = A3) since it has a
  physical unit, while the broadband `centroid` and β/α sources stay session-relative
  like every other drive here. Direction still carries no valence — higher is not
  better, it is just faster.
- **Visuals are intentionally slow/forgiving** (particle shimmer, smooth lerps) to
  hide FFT jitter rather than expose it. Don't make the field twitchy.

## Known traps (each has cost me time)

- **Mixed-content wall.** Browsers BLOCK `ws://` from an `https://` page. The
  claude.ai artifact iframe is https, so it can't reach `ws://localhost` — you
  MUST run the HTML locally. Not a bug, browser security.
- **BrainFlow API drifts across versions.** `perform_bandpass` changed signature
  (old: center/bandwidth; new ≥5: start/stop). We skip explicit bandpass and let
  Welch handle it, to dodge this. Verify `get_exg_channels`,
  `remove_environmental_noise`, `get_current_board_data` against the installed
  version if anything errors.
- **`websockets` handler signature.** Newer calls `handler(ws)`; some older
  versions call `handler(ws, path)`. Add `path` if connect throws.
- **The EMG sentinel is a heuristic**, not myography: high-freq (30–45 Hz) power
  as a fraction of total. The 60 Hz notch punches a hole through that band, so it's
  approximate. Good enough to freeze feedback on a jaw-clench; not calibrated.
- **`json.dumps` emits bare `NaN`, and `JSON.parse` rejects it.** Any new feature that
  can be undefined (PAF with no peak, centroid on an empty band) must be sent as
  `None`, not a NaN float, or the front-end's socket handler throws on that message.
- **Normalization warmup.** `RunningNorm` returns 0.5 until its buffer fills (~first
  10 samples / a few seconds). Expect a neutral start.

## The validation gate — run this FIRST on real hardware

**Alpha-blocking (Berger, 1929):** eyes closed → occipital alpha surges → eyes
open → it craters. If the aurora field visibly swells and collapses with your
eyelids, the whole chain (electrodes → BrainFlow → filter → PSD → norm → socket →
render) is proven end-to-end in one gesture. If it doesn't, it's a
montage/impedance/reference problem — no downstream tuning will fix it. Don't trust
any χ/PAF number until this passes. Occipital sites (O1/O2/Pz) show alpha strongest.

## Open threads (roughly what's next)

1. **Wire the scope to real PSD.** Server already sends `freqs/logpsd`; the scope's
   `fitAperiodic()`/`findPAF()` already work on any log-power array. Snippet is in
   `eeg_server.py`. Replace `synthPSD()` body with the received spectrum, kill `drift()`.
2. **Add a knee to the aperiodic model.** Real resting EEG bends below ~2 Hz; the
   current knee-free `offset − χ·log10(f)` fit masks <2 Hz to cope. specparam's knee
   param is the proper fix if reporting χ.
3. **Individualize bands relative to PAF** (Klimesch IAF-anchored bands) instead of
   fixed 8–12 Hz, once PAF is trusted — a fixed band mis-slices people whose peak is
   8.5 vs 11.5.
4. **Offline specparam** for anything reportable; treat the online OLS-slope proxy as
   a monitor, not a measurement.

## Conventions

- Front-ends are **single-file vanilla JS + canvas, zero dependencies**. Keep them
  that way — no React/build step. CSS uses custom properties in `:root`.
- Python deps live in `requirements.txt`; don't add heavy frameworks.
- The server's spectral math (fit/PAF) intentionally mirrors the scope's JS so both
  agree. If you change one, change the other.
