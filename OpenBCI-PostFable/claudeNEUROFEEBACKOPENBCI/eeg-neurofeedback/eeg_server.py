#!/usr/bin/env python3
"""
eeg_server.py  —  OpenBCI Cyton -> WebSocket bridge for the aurora + scope apps.

Acquires a primary channel pair plus an optional Pz channel via BrainFlow, filters
them, computes Welch PSDs, and derives:
  band  : normalized (0..1) power in your target band       -> drives the aurora field
  emg   : high-frequency power fraction (0..1)               -> the EMG sentinel
  ch1/2 : primary-pair normalized band power (0..1)          -> the two channel meters
  posterior : artifact-gated Pz vigilance/drowsiness proxies -> adaptive feedback
  paf   : peak alpha frequency (Hz), 1/f-removed             -> the scope's PAF marker
  chi   : aperiodic exponent (spectrum ~ 1/f^chi)            -> the scope's slope readout
  centroid : power-weighted mean frequency (Hz), 2-40        -> the aurora's audio pitch
  freqs/logpsd : a decimated PSD                             -> the scope's live spectrum

Two ways to run:
  1) NO HARDWARE (test the whole pipeline end-to-end):
        python eeg_server.py --board synthetic
  2) REAL CYTON:
        python eeg_server.py --board cyton --serial-port COM3          (Windows)
        python eeg_server.py --board cyton --serial-port /dev/ttyUSB0  (Linux)
        python eeg_server.py --board cyton --serial-port /dev/cu.usbserial-XXXX  (macOS)
     CYTON + DAISY:
        python eeg_server.py --board cyton-daisy --serial-port /dev/cu.usbserial-XXXX

Then open one of the HTML apps and point it at ws://localhost:8765 (see the seam
notes at the bottom of this file).

Requires:  pip install brainflow numpy scipy websockets

* MIXED-CONTENT GOTCHA *  A browser will BLOCK a ws:// (insecure) socket if the page
itself is served over https:// — which the claude.ai artifact iframe is. So to consume
this stream you must run the HTML LOCALLY (open the .html via a local server or file://),
not from inside claude.ai. Locally, ws://localhost works fine.
"""

import argparse, asyncio, json, sys, time
from collections import deque

import numpy as np
from scipy.signal import welch

from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds
from brainflow.data_filter import DataFilter, NoiseTypes, DetrendOperations

# ------------------------------------------------------------------ helpers

START_BYTE = 0xA0
PACKET_LEN = 33
CYTON_SCALE_UV = 4.5 / 24.0 / (2**23 - 1) * 1_000_000.0


def _int24(raw3):
    value = (raw3[0] << 16) | (raw3[1] << 8) | raw3[2]
    return value - (1 << 24) if value & 0x800000 else value


class DirectCytonSerial:
    """Small direct-serial fallback for boards BrainFlow cannot prepare.

    The Cyton radio still emits standard 33-byte packets. This reader preserves the
    existing DSP/normalization pipeline while bypassing only BrainFlow's session
    handshake.
    """
    def __init__(self, port, baud=115200, timeout=0.05):
        import serial
        self.serial = serial.Serial(port, baud, timeout=timeout)
        self.buffer = bytearray()

    def start(self):
        time.sleep(0.8)
        self.serial.reset_input_buffer()
        self.serial.write(b"b")
        self.serial.flush()
        time.sleep(0.4)

    def read_packets(self, max_packets=512):
        chunk = self.serial.read(4096)
        if chunk:
            self.buffer.extend(chunk)
        packets = []
        while len(packets) < max_packets:
            start = self.buffer.find(bytes([START_BYTE]))
            if start < 0:
                self.buffer.clear()
                break
            if start:
                del self.buffer[:start]
            if len(self.buffer) < PACKET_LEN:
                break
            packet = bytes(self.buffer[:PACKET_LEN])
            del self.buffer[:PACKET_LEN]
            if not (0xC0 <= packet[-1] <= 0xCF):
                continue
            values = [
                _int24(packet[2 + 3*i:5 + 3*i]) * CYTON_SCALE_UV
                for i in range(8)
            ]
            packets.append(values)
        return np.asarray(packets, dtype=float)

    def stop(self):
        try:
            self.serial.write(b"s")
            self.serial.flush()
        finally:
            self.serial.close()

class RunningNorm:
    """Adaptive 0..1 normalizer: robust z-score over a rolling window, logistic-squashed.
    Absolute EEG band power is meaningless across people/sessions (impedance, skull),
    so we normalize to the subject's own recent distribution instead of hardcoding gains."""
    def __init__(self, n=200):
        self.buf = deque(maxlen=n)
    def push(self, x):
        self.buf.append(x)
        if len(self.buf) < 10:
            return 0.5
        arr = np.array(self.buf)
        med = np.median(arr)
        # robust spread via MAD -> approx std
        mad = np.median(np.abs(arr - med)) + 1e-12
        z = (x - med) / (1.4826 * mad)
        return float(1.0 / (1.0 + np.exp(-z)))   # logistic squash to 0..1


def fit_aperiodic(freqs, psd, fit_lo=2.0, fit_hi=45.0):
    """OLS slope of log10(power) vs log10(freq), MASKING the oscillatory bands so
    peaks don't bias the background fit. Returns (chi, offset, fitted_logpsd_full)."""
    logf = np.log10(freqs)
    logp = np.log10(psd + 1e-30)
    mask = (freqs >= fit_lo) & (freqs <= fit_hi)
    mask &= ~((freqs >= 7) & (freqs <= 14))     # mask alpha
    mask &= ~((freqs >= 16) & (freqs <= 30))    # mask beta
    x, y = logf[mask], logp[mask]
    A = np.vstack([x, np.ones_like(x)]).T
    slope, intercept = np.linalg.lstsq(A, y, rcond=None)[0]
    fitted = intercept + slope * logf
    return -slope, intercept, fitted           # chi = -slope


def find_paf(freqs, values, lo=7.0, hi=14.0, df=None):
    """Parabolic-interpolated peak of `values` (pass the 1/f-REMOVED residual, not raw
    power) within the alpha window -> sub-bin PAF in Hz."""
    idx = np.where((freqs >= lo) & (freqs <= hi))[0]
    if len(idx) == 0:
        return float('nan')
    k = idx[np.argmax(values[idx])]
    if k <= 0 or k >= len(freqs) - 1:
        return float(freqs[k])
    ym1, y0, yp1 = values[k-1], values[k], values[k+1]
    denom = (ym1 - 2*y0 + yp1)
    d = 0.5 * (ym1 - yp1) / denom if denom != 0 else 0.0
    d = float(np.clip(d, -0.5, 0.5))
    step = df if df is not None else (freqs[1] - freqs[0])
    return float(freqs[k] + d * step)


def band_power(freqs, psd, lo, hi):
    m = (freqs >= lo) & (freqs < hi)
    return float(np.trapz(psd[m], freqs[m])) if m.any() else 0.0


def normalized_spectral_entropy(psd):
    """Normalized Shannon entropy of the 1–45 Hz power distribution.

    A narrow spectrum approaches 0; power spread across many frequencies
    approaches 1. This is a spectral-complexity proxy, not a clinical measure.
    """
    power = np.clip(np.asarray(psd, dtype=float), 0, None)
    total = float(np.sum(power))
    if total <= 0 or power.size < 2:
        return float('nan')
    prob = power / total
    entropy = -float(np.sum(prob * np.log(prob + 1e-30)))
    return float(np.clip(entropy / np.log(power.size), 0, 1))


def channel_diagnostics(slot, exg_index, sig, fs, line_hz, noise_type):
    """Per-ELECTRODE health, computed before the channels are averaged together.

    The main pipeline averages both channels before it derives anything, which is right
    for feedback and useless for triage: a single dead lead poisons the average and you
    cannot tell which one it was. These four numbers separate the cases:

      rms_uv    raw amplitude. Scalp EEG is ~5-50 uV. Hundreds of uV is muscle;
                thousands means the input is floating, not measuring.
      emg       the same high-frequency ratio the feedback uses, but per channel.
      chi       aperiodic exponent per channel. Real EEG is ~1-2; a flat spectrum
                (chi near 0) is a noise source, not a brain.
      mains     55-65 Hz power as a fraction of 1-45 Hz, measured BEFORE the notch.
                A big number here means common-mode rejection has failed, which points
                at the shared reference or bias lead rather than this electrode.

    Read it as: one channel hot = that signal electrode. BOTH channels hot = the leads
    they share, i.e. reference or bias.
    """
    out = {"slot": slot, "exg": int(exg_index)}
    out["rms_uv"] = round(float(np.sqrt(np.mean(sig ** 2))), 2)

    nper = min(len(sig), int(fs * 2))
    freqs_raw, p_raw = welch(sig, fs=fs, nperseg=nper, noverlap=nper // 2)
    broadband = band_power(freqs_raw, p_raw, 1.0, 45.0) + 1e-30
    out["mains"] = round(band_power(freqs_raw, p_raw, line_hz - 5.0, line_hz + 5.0) / broadband, 4)

    # remove_environmental_noise wants the NoiseTypes enum value, NOT a frequency in Hz.
    # Passing 60.0 raises INVALID_ARGUMENTS_ERROR and takes the whole payload down with it.
    notched = np.ascontiguousarray(sig.copy())
    DataFilter.remove_environmental_noise(notched, fs, noise_type)
    freqs, p = welch(notched, fs=fs, nperseg=nper, noverlap=nper // 2)
    keep = (freqs >= 1) & (freqs <= 45)
    freqs, p = freqs[keep], p[keep]
    total = band_power(freqs, p, 1.0, 45.0) + 1e-30
    # rms_uv counts everything including sub-1 Hz wander; this counts only the band we
    # actually use. rms_uv >> rms_band_uv means the channel is drifting, not noisy.
    out["rms_band_uv"] = round(float(np.sqrt(max(total, 0.0))), 2)
    out["emg"] = round(float(np.clip(band_power(freqs, p, 30.0, 45.0) / total * 4.0, 0, 1)), 4)
    try:
        chi, _, _ = fit_aperiodic(freqs, p)
        out["chi"] = round(float(chi), 3)
    except Exception:
        out["chi"] = None
    return out


def spectral_centroid(freqs, psd, lo=2.0, hi=40.0):
    """Power-weighted mean frequency (Hz) — one scalar for "how fast is the spectrum
    running right now". It falls as slow rhythms (delta/theta/alpha) take over and
    rises as power shifts to beta. Unlike PAF it is always defined, which is what an
    audio mapping needs: an eyes-closed listener must never hear the tone drop out.
    Stops at 40 Hz so mains leakage and EMG can't drag the pitch up on a jaw clench.
    Absolute value is montage-dependent — the front-end sonifies its DEVIATION from
    the session baseline, the same contract as band power."""
    m = (freqs >= lo) & (freqs < hi)
    if not m.any():
        return float('nan')
    w = psd[m]
    total = float(np.sum(w))
    if total <= 0:
        return float('nan')
    return float(np.sum(freqs[m] * w) / total)


# ------------------------------------------------------------------ acquisition + DSP

class EEGPipeline:
    def __init__(self, args):
        self.args = args
        params = BrainFlowInputParams()
        self.direct_serial = args.board == "cyton-serial"
        self.raw_buffer = np.empty((8, 0), dtype=float)

        if self.direct_serial:
            if not args.serial_port:
                sys.exit("Cyton needs --serial-port (e.g. COM3, /dev/ttyUSB0, /dev/cu.usbserial-XXXX)")
            self.board_id = None
            self.board = DirectCytonSerial(args.serial_port)
            self.fs = int(args.serial_fs)
            exg = list(range(8))
        elif args.board in ("cyton", "cyton-daisy"):
            if not args.serial_port:
                sys.exit("Cyton needs --serial-port (e.g. COM3, /dev/ttyUSB0, /dev/cu.usbserial-XXXX)")
            params.serial_port = args.serial_port
            params.timeout = 15
            self.board_id = (
                BoardIds.CYTON_DAISY_BOARD.value
                if args.board == "cyton-daisy"
                else BoardIds.CYTON_BOARD.value
            )
        else:
            self.board_id = BoardIds.SYNTHETIC_BOARD.value

        if not self.direct_serial:
            self.board = BoardShim(self.board_id, params)
            self.fs = BoardShim.get_sampling_rate(self.board_id)
            exg = BoardShim.get_exg_channels(self.board_id)
        # Pick the two primary channel indices (0-based into the exg list). An
        # optional Pz channel is analyzed separately and does not replace either
        # member of the existing pair.
        c = args.channels
        requested = (
            list(c)
            + ([] if args.pz_channel is None else [args.pz_channel])
            + (
                []
                if args.posterior_right_channel is None
                else [args.posterior_right_channel]
            )
        )
        if any(index < 0 or index >= len(exg) for index in requested):
            sys.exit(
                f"Requested EXG index outside 0..{len(exg) - 1}: {requested}"
            )
        self.primary_chans = [exg[c[0]], exg[c[1]]]
        self.pz_chan = None if args.pz_channel is None else exg[args.pz_channel]
        self.posterior_right_chan = (
            None
            if args.posterior_right_channel is None
            else exg[args.posterior_right_channel]
        )
        self.chans = list(self.primary_chans)
        if self.pz_chan is not None and self.pz_chan not in self.chans:
            self.chans.append(self.pz_chan)
        if (
            self.posterior_right_chan is not None
            and self.posterior_right_chan not in self.chans
        ):
            self.chans.append(self.posterior_right_chan)
        self.pz_slot = (
            self.chans.index(self.pz_chan) if self.pz_chan is not None else None
        )
        self.posterior_right_slot = (
            self.chans.index(self.posterior_right_chan)
            if self.posterior_right_chan is not None
            else None
        )
        self.win = int(args.window * self.fs)     # samples in the analysis window

        # target band
        self.band_lo, self.band_hi = (8.0, 12.0) if args.band == "alpha" else (12.0, 30.0)

        # normalizers
        self.norm = RunningNorm()
        self.norm1 = RunningNorm()
        self.norm2 = RunningNorm()
        self.alpha_norm = RunningNorm()
        self.alpha_norm1 = RunningNorm()
        self.alpha_norm2 = RunningNorm()
        self.beta_norm = RunningNorm()
        self.beta_norm1 = RunningNorm()
        self.beta_norm2 = RunningNorm()
        self.pz_alpha_norm = RunningNorm()
        self.pz_beta_norm = RunningNorm()
        self.pz_theta_alpha_norm = RunningNorm()
        self.pz_slow_norm = RunningNorm()
        self.pz_engagement_norm = RunningNorm()
        self.posterior_right_alpha_norm = RunningNorm()
        self.posterior_right_beta_norm = RunningNorm()
        self.posterior_right_theta_alpha_norm = RunningNorm()
        self.posterior_right_slow_norm = RunningNorm()
        self.posterior_right_engagement_norm = RunningNorm()

        self.line = NoiseTypes.SIXTY.value if args.line == 60 else NoiseTypes.FIFTY.value

        pz_config = (
            "off"
            if args.pz_channel is None
            else f"exg-idx={args.pz_channel} -> chan={self.pz_chan}"
        )
        posterior_right_config = (
            "off"
            if args.posterior_right_channel is None
            else (
                f"exg-idx={args.posterior_right_channel}"
                f" -> chan={self.posterior_right_chan}"
            )
        )
        print(
            f"[cfg] board={args.board}  fs={self.fs}Hz  "
            f"primary-exg-idx={c} -> chans={self.primary_chans}  "
            f"Pz={pz_config}  right-posterior={posterior_right_config}"
        )
        print(f"[cfg] band={args.band} ({self.band_lo}-{self.band_hi}Hz)  window={args.window}s "
              f"({self.win} samp)  line={args.line}Hz")

    def start(self):
        if self.direct_serial:
            self.board.start()
        else:
            self.board.prepare_session()
            self.board.start_stream()

    def stop(self):
        if self.direct_serial:
            self.board.stop()
            return
        try:
            self.board.stop_stream(); self.board.release_session()
        except Exception:
            pass

    def _preprocess(self, sig):
        """In-place BrainFlow filtering on one channel."""
        DataFilter.detrend(sig, DetrendOperations.LINEAR.value)
        # remove_environmental_noise applies a notch at the mains frequency
        DataFilter.remove_environmental_noise(sig, self.fs, self.line)
        # --- optional bandpass. NOTE: BrainFlow's perform_bandpass signature CHANGED
        # across versions. Recent (>=5) is (data, fs, start_freq, stop_freq, order, type, ripple).
        # Older is (data, fs, center_freq, band_width, ...). scipy.welch already handles the
        # frequency content we care about, so we skip an explicit bandpass to avoid the
        # version mismatch. Add it back if your build wants it.
        return sig

    def compute(self):
        if self.direct_serial:
            packets = self.board.read_packets()
            if packets.size:
                self.raw_buffer = np.hstack((self.raw_buffer, packets.T))
                self.raw_buffer = self.raw_buffer[:, -self.win:]
            data = self.raw_buffer
        else:
            data = self.board.get_current_board_data(self.win)

        if data.shape[1] < self.win:
            return None   # not enough samples buffered yet

        psds, chvals = [], []
        for ch in self.chans:
            # Filtering is in-place; copy so the later raw-channel diagnostics
            # still see the pre-notch signal and can measure mains contamination.
            sig = np.array(
                data[ch][-self.win:], dtype=np.float64, order="C", copy=True
            )
            sig = self._preprocess(sig)
            nper = min(len(sig), int(self.fs * 2))         # ~2s Welch segments
            freqs, p = welch(sig, fs=self.fs, nperseg=nper, noverlap=nper // 2)
            keep = (freqs >= 1) & (freqs <= 45)
            freqs, p = freqs[keep], p[keep]
            psds.append(p)
            chvals.append(band_power(freqs, p, self.band_lo, self.band_hi))

        # Per-electrode triage, on the detrended signal only — the averaging below
        # destroys the information about WHICH lead is misbehaving.
        chan_diag, detrended = [], []
        for slot_index, ch in enumerate(self.chans):
            raw = np.ascontiguousarray(data[ch][-self.win:], dtype=np.float64)
            DataFilter.detrend(raw, DetrendOperations.LINEAR.value)
            detrended.append(raw)
            diag = channel_diagnostics(
                slot_index + 1, ch, raw, self.fs, float(self.args.line), self.line
            )
            diag["role"] = (
                "Pz"
                if self.pz_slot == slot_index
                else (
                    "right-posterior (~P4/O2)"
                    if self.posterior_right_slot == slot_index
                    else f"primary-{slot_index + 1}"
                )
            )
            chan_diag.append(diag)

        # ch1 - ch2 cancels the shared reference exactly (both are V(electrode)-V(ref)),
        # so this is the TRUE potential difference between the two scalp electrodes.
        # Near the amplifier noise floor means they are seeing the same thing, i.e.
        # shorted together — a paste bridge — regardless of how big each channel looks.
        diff_rms = float(np.sqrt(np.mean((detrended[0] - detrended[1]) ** 2)))

        pz_contact_clean = False
        pz_quality_reason = "not configured"
        posterior_right_contact_clean = False
        posterior_right_quality_reason = "not configured"

        def contact_quality(slot):
            diag = chan_diag[slot]
            clean = bool(
                diag["rms_band_uv"] <= self.args.pz_max_rms_uv
                and diag["mains"] <= self.args.pz_max_mains_ratio
                and diag["emg"] <= 0.25
            )
            reasons = []
            if diag["rms_band_uv"] > self.args.pz_max_rms_uv:
                reasons.append("amplitude")
            if diag["mains"] > self.args.pz_max_mains_ratio:
                reasons.append("mains")
            if diag["emg"] > 0.25:
                reasons.append("EMG")
            return clean, ("clean" if not reasons else "+".join(reasons))

        if self.pz_slot is not None:
            pz_contact_clean, pz_quality_reason = contact_quality(self.pz_slot)
        if self.posterior_right_slot is not None:
            (
                posterior_right_contact_clean,
                posterior_right_quality_reason,
            ) = contact_quality(self.posterior_right_slot)

        primary_psd = np.mean(psds[:2], axis=0)
        clean_posterior_slots = []
        if self.pz_slot is not None and pz_contact_clean:
            clean_posterior_slots.append(self.pz_slot)
        if (
            self.posterior_right_slot is not None
            and posterior_right_contact_clean
        ):
            clean_posterior_slots.append(self.posterior_right_slot)
        # Preserve the old pair and give the posterior ensemble half the global
        # influence. Each posterior lead must pass independently; a floating lead
        # remains visible in diagnostics but cannot poison the feedback.
        psd = (
            primary_psd
            if not clean_posterior_slots
            else (
                0.5 * primary_psd
                + 0.5 * np.mean(
                    [psds[slot] for slot in clean_posterior_slots], axis=0
                )
            )
        )

        # --- alpha + beta + EMG (normalized 0..1) ---
        # Both normalized bands are transported so the Aurora UI can switch between
        # focus (beta) and relax (alpha) without restarting acquisition.
        alpha_vals = [band_power(freqs, p, 8.0, 12.0) for p in psds]
        beta_vals = [band_power(freqs, p, 12.0, 30.0) for p in psds]
        alpha = self.alpha_norm.push(band_power(freqs, psd, 8.0, 12.0))
        alpha_ch1 = self.alpha_norm1.push(alpha_vals[0])
        alpha_ch2 = self.alpha_norm2.push(alpha_vals[1])
        beta = self.beta_norm.push(band_power(freqs, psd, 12.0, 30.0))
        beta_ch1 = self.beta_norm1.push(beta_vals[0])
        beta_ch2 = self.beta_norm2.push(beta_vals[1])
        alpha_pz = (
            self.pz_alpha_norm.push(alpha_vals[self.pz_slot])
            if self.pz_slot is not None and pz_contact_clean
            else None
        )
        beta_pz = (
            self.pz_beta_norm.push(beta_vals[self.pz_slot])
            if self.pz_slot is not None and pz_contact_clean
            else None
        )
        alpha_posterior_right = (
            self.posterior_right_alpha_norm.push(
                alpha_vals[self.posterior_right_slot]
            )
            if (
                self.posterior_right_slot is not None
                and posterior_right_contact_clean
            )
            else None
        )
        beta_posterior_right = (
            self.posterior_right_beta_norm.push(
                beta_vals[self.posterior_right_slot]
            )
            if (
                self.posterior_right_slot is not None
                and posterior_right_contact_clean
            )
            else None
        )

        if self.args.band == "alpha":
            band, ch1, ch2 = alpha, alpha_ch1, alpha_ch2
        else:
            band, ch1, ch2 = beta, beta_ch1, beta_ch2

        delta_power = band_power(freqs, psd, 1.0, 4.0)
        theta_power = band_power(freqs, psd, 4.0, 8.0)
        alpha_power = band_power(freqs, psd, 8.0, 12.0)
        beta_power = band_power(freqs, psd, 12.0, 30.0)
        gamma_power = band_power(freqs, psd, 30.0, 45.0)
        total = delta_power + theta_power + alpha_power + beta_power + gamma_power + 1e-30
        # Reject the noisiest trusted lead. A posterior lead that already failed
        # independent contact checks is excluded rather than freezing otherwise
        # usable primary feedback.
        per_channel_emg = []
        for channel_psd in psds:
            channel_total = band_power(freqs, channel_psd, 1.0, 45.0) + 1e-30
            per_channel_emg.append(
                float(np.clip(
                    band_power(freqs, channel_psd, 30.0, 45.0)
                    / channel_total * 4.0,
                    0,
                    1,
                ))
            )
        trusted_slots = [0, 1] + clean_posterior_slots
        emg = max(per_channel_emg[slot] for slot in trusted_slots)
        engagement = float(beta_power / (alpha_power + theta_power + 1e-30))
        centroid = spectral_centroid(freqs, psd)
        spectral_entropy = normalized_spectral_entropy(psd)

        # --- aperiodic + PAF ---
        chi, offset, fitted = fit_aperiodic(freqs, psd)
        resid = np.log10(psd + 1e-30) - fitted
        global_paf = find_paf(freqs, resid, df=freqs[1] - freqs[0])

        posterior = None
        posterior_sites = {}
        paf = global_paf
        alpha_mask = (freqs >= 7.0) & (freqs <= 14.0)

        def posterior_site_metrics(
            slot, contact_clean, quality_reason, key, site, channel, norms
        ):
            site_psd = psds[slot]
            delta = band_power(freqs, site_psd, 1.0, 4.0)
            theta = band_power(freqs, site_psd, 4.0, 8.0)
            alpha_power_site = band_power(freqs, site_psd, 8.0, 12.0)
            beta_power_site = band_power(freqs, site_psd, 12.0, 30.0)
            gamma = band_power(freqs, site_psd, 30.0, 45.0)
            total_site = (
                delta + theta + alpha_power_site + beta_power_site + gamma + 1e-30
            )
            theta_alpha = float(theta / (alpha_power_site + 1e-30))
            engagement_site = float(
                beta_power_site / (theta + alpha_power_site + 1e-30)
            )
            slow_fast = float(
                (delta + theta)
                / (alpha_power_site + beta_power_site + 1e-30)
            )
            entropy_site = normalized_spectral_entropy(site_psd)
            centroid_site = spectral_centroid(freqs, site_psd)
            chi_site, _, fitted_site = fit_aperiodic(freqs, site_psd)
            resid_site = np.log10(site_psd + 1e-30) - fitted_site
            paf_site = find_paf(
                freqs, resid_site, df=freqs[1] - freqs[0]
            )
            alpha_mask = (freqs >= 7.0) & (freqs <= 14.0)
            paf_prominence = float(
                np.max(resid_site[alpha_mask])
                - np.median(resid_site[alpha_mask])
            )
            paf_confidence = float(np.clip(paf_prominence / 0.35, 0, 1))
            site_emg = per_channel_emg[slot]
            clean = bool(
                contact_clean
                and np.isfinite(theta_alpha)
                and np.isfinite(engagement_site)
            )

            # All three scores are adaptive within-person ranks, not population
            # thresholds. Theta/alpha and slow/fast rise with drowsier posterior
            # spectra; beta/(theta+alpha) moves in the opposite direction.
            if clean:
                theta_alpha_score = norms["theta_alpha"].push(
                    np.log(theta_alpha + 1e-30)
                )
                slow_score = norms["slow"].push(
                    np.log(slow_fast + 1e-30)
                )
                engagement_score = norms["engagement"].push(
                    np.log(engagement_site + 1e-30)
                )
            else:
                # Do not teach the personal baseline what a floating/noisy
                # electrode looks like. Scores resume from neutral once clean.
                theta_alpha_score = slow_score = engagement_score = 0.5
            drowsiness = float(
                np.clip(0.72 * theta_alpha_score + 0.28 * slow_score, 0, 1)
            )
            vigilance = float(np.clip(
                0.48 * engagement_score
                + 0.37 * (1.0 - theta_alpha_score)
                + 0.15 * (1.0 - slow_score),
                0,
                1,
            ))
            # Exploratory on-task proxy: useful as a reward feature, never a
            # diagnosis or a literal detector of thoughts/daydreams.
            on_task_proxy = float(np.clip(
                0.60 * engagement_score + 0.40 * (1.0 - slow_score), 0, 1
            ))
            diag = chan_diag[slot]
            return {
                "key": key,
                "site": site,
                "channel": int(channel + 1),
                "clean": clean,
                "quality_reason": quality_reason,
                "rms_band_uv": diag["rms_band_uv"],
                "mains_ratio": diag["mains"],
                "theta_alpha": round(theta_alpha, 5),
                "slow_fast": round(slow_fast, 5),
                "engagement": round(engagement_site, 5),
                "centroid": (
                    None
                    if not np.isfinite(centroid_site)
                    else round(centroid_site, 3)
                ),
                "paf": None if not np.isfinite(paf_site) else round(paf_site, 3),
                "paf_confidence": round(paf_confidence, 4),
                "chi": round(float(chi_site), 4),
                "emg": round(site_emg, 4),
                "spectral_entropy": (
                    None
                    if not np.isfinite(entropy_site)
                    else round(entropy_site, 5)
                ),
                "vigilance": round(vigilance, 4),
                "drowsiness": round(drowsiness, 4),
                "on_task_proxy": round(on_task_proxy, 4),
                "bands": {
                    "delta": round(float(delta / total_site), 6),
                    "theta": round(float(theta / total_site), 6),
                    "alpha": round(float(alpha_power_site / total_site), 6),
                    "beta": round(float(beta_power_site / total_site), 6),
                    "gamma": round(float(gamma / total_site), 6),
                },
            }

        if self.pz_slot is not None:
            posterior_sites["pz"] = posterior_site_metrics(
                self.pz_slot,
                pz_contact_clean,
                pz_quality_reason,
                "pz",
                "Pz",
                self.args.pz_channel,
                {
                    "theta_alpha": self.pz_theta_alpha_norm,
                    "slow": self.pz_slow_norm,
                    "engagement": self.pz_engagement_norm,
                },
            )
        if self.posterior_right_slot is not None:
            posterior_sites["right_posterior"] = posterior_site_metrics(
                self.posterior_right_slot,
                posterior_right_contact_clean,
                posterior_right_quality_reason,
                "right_posterior",
                "~P4/O2",
                self.args.posterior_right_channel,
                {
                    "theta_alpha": self.posterior_right_theta_alpha_norm,
                    "slow": self.posterior_right_slow_norm,
                    "engagement": self.posterior_right_engagement_norm,
                },
            )

        configured_sites = list(posterior_sites.values())
        clean_sites = [site for site in configured_sites if site["clean"]]
        if configured_sites:
            score_sites = clean_sites if clean_sites else configured_sites

            def mean_field(field, default=0.5):
                values = [
                    float(site[field])
                    for site in score_sites
                    if site.get(field) is not None
                    and np.isfinite(float(site[field]))
                ]
                return float(np.mean(values)) if values else default

            def geometric_mean_field(field, default=1.0):
                values = [
                    max(float(site[field]), 1e-30)
                    for site in score_sites
                    if site.get(field) is not None
                    and np.isfinite(float(site[field]))
                ]
                return (
                    float(np.exp(np.mean(np.log(values))))
                    if values
                    else default
                )

            best_paf_site = (
                max(clean_sites, key=lambda site: site["paf_confidence"])
                if clean_sites
                else None
            )
            if (
                best_paf_site is not None
                and best_paf_site["paf"] is not None
                and best_paf_site["paf_confidence"] >= 0.15
            ):
                paf = best_paf_site["paf"]

            band_names = ("delta", "theta", "alpha", "beta", "gamma")
            combined_bands = {
                name: round(
                    float(np.mean([site["bands"][name] for site in score_sites])),
                    6,
                )
                for name in band_names
            }
            posterior = {
                "site": "posterior ensemble",
                "clean": bool(clean_sites),
                "sites_total": len(configured_sites),
                "sites_clean": len(clean_sites),
                "clean_labels": [site["site"] for site in clean_sites],
                "quality_reason": "; ".join(
                    f'{site["site"]}:{site["quality_reason"]}'
                    for site in configured_sites
                ),
                "rms_band_uv": round(
                    max(site["rms_band_uv"] for site in configured_sites), 2
                ),
                "mains_ratio": round(
                    max(site["mains_ratio"] for site in configured_sites), 4
                ),
                "theta_alpha": round(geometric_mean_field("theta_alpha"), 5),
                "slow_fast": round(geometric_mean_field("slow_fast"), 5),
                "engagement": round(geometric_mean_field("engagement"), 5),
                "centroid": round(mean_field("centroid", float("nan")), 3),
                "paf": (
                    None if best_paf_site is None else best_paf_site["paf"]
                ),
                "paf_confidence": (
                    0.0
                    if best_paf_site is None
                    else best_paf_site["paf_confidence"]
                ),
                "chi": round(mean_field("chi", float("nan")), 4),
                "emg": round(max(site["emg"] for site in configured_sites), 4),
                "spectral_entropy": round(
                    mean_field("spectral_entropy", float("nan")), 5
                ),
                "vigilance": round(mean_field("vigilance"), 4),
                "drowsiness": round(mean_field("drowsiness"), 4),
                "on_task_proxy": round(mean_field("on_task_proxy"), 4),
                "bands": combined_bands,
            }

        # --- decimate PSD for transport (scope draws this) ---
        step = max(1, len(freqs) // 120)
        f_d = freqs[::step]
        lp_d = np.log10(psd[::step] + 1e-30)

        return {
            "timestamp": round(time.time(), 3),
            "band": round(band, 4), "emg": round(emg, 4),
            "ch1": round(ch1, 4), "ch2": round(ch2, 4),
            "alpha": round(alpha, 4),
            "alpha_ch1": round(alpha_ch1, 4), "alpha_ch2": round(alpha_ch2, 4),
            "alpha_pz": None if alpha_pz is None else round(alpha_pz, 4),
            "alpha_posterior_right": (
                None
                if alpha_posterior_right is None
                else round(alpha_posterior_right, 4)
            ),
            "beta": round(beta, 4),
            "beta_ch1": round(beta_ch1, 4), "beta_ch2": round(beta_ch2, 4),
            "beta_pz": None if beta_pz is None else round(beta_pz, 4),
            "beta_posterior_right": (
                None
                if beta_posterior_right is None
                else round(beta_posterior_right, 4)
            ),
            "paf": round(paf, 3), "chi": round(float(chi), 4),
            # null, not NaN: json.dumps would emit bare NaN and JSON.parse rejects it
            "centroid": None if not np.isfinite(centroid) else round(centroid, 3),
            "channels": chan_diag,
            "montage": {
                "primary": [int(index + 1) for index in self.args.channels],
                "pz": (
                    None
                    if self.args.pz_channel is None
                    else int(self.args.pz_channel + 1)
                ),
                "posterior_right": (
                    None
                    if self.args.posterior_right_channel is None
                    else int(self.args.posterior_right_channel + 1)
                ),
            },
            "posterior": posterior,
            "posterior_sites": posterior_sites,
            "diff_rms_uv": round(diff_rms, 2),
            "spectral_entropy": (
                None if not np.isfinite(spectral_entropy) else round(spectral_entropy, 5)
            ),
            "offset": round(float(offset), 4),
            "engagement": round(engagement, 5),
            "bands": {
                "delta": round(float(delta_power / total), 6),
                "theta": round(float(theta_power / total), 6),
                "alpha": round(float(alpha_power / total), 6),
                "beta": round(float(beta_power / total), 6),
                "gamma": round(float(gamma_power / total), 6),
            },
            "freqs": [round(float(x), 2) for x in f_d],
            "logpsd": [round(float(x), 3) for x in lp_d],
        }


# ------------------------------------------------------------------ websocket

async def main():
    import websockets   # imported here so --help works without it installed

    ap = argparse.ArgumentParser()
    ap.add_argument("--board", choices=["synthetic", "cyton", "cyton-daisy", "cyton-serial"], default="synthetic")
    ap.add_argument("--serial-port", default=None)
    ap.add_argument("--serial-fs", type=float, default=250.0,
                    help="packet rate for --board cyton-serial")
    ap.add_argument("--band", choices=["alpha", "beta"], default="alpha",
                    help="alpha is the easiest first target: big eyes-closed peak")
    ap.add_argument("--channels", type=int, nargs=2, default=[0, 1],
                    help="two 0-based indices into the board's exg channel list")
    ap.add_argument("--pz-channel", type=int, default=None,
                    help="optional 0-based EXG index for a separately analyzed Pz lead")
    ap.add_argument("--posterior-right-channel", type=int, default=None,
                    help="optional 0-based EXG index near right P4/O2")
    ap.add_argument("--pz-max-rms-uv", type=float, default=250.0,
                    help="exclude Pz above this 1-45 Hz RMS amplitude")
    ap.add_argument("--pz-max-mains-ratio", type=float, default=0.5,
                    help="exclude Pz when 55-65 Hz pickup exceeds this ratio")
    ap.add_argument("--line", type=int, choices=[50, 60], default=60,
                    help="mains frequency (60 US / 50 EU)")
    ap.add_argument("--window", type=float, default=4.0,
                    help="analysis window seconds; 4s gives ~0.25Hz resolution for PAF")
    ap.add_argument("--interval", type=float, default=0.25, help="seconds between updates")
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()

    pipe = EEGPipeline(args)
    pipe.start()
    print(f"[ws] serving ws://{args.host}:{args.port}   (Ctrl-C to stop)")
    print("[tip] eyes-closed -> alpha should surge, eyes-open -> it craters."
          "  If that shows, your pipeline is real.")

    clients = set()

    async def handler(ws):                # NOTE: some older `websockets` versions call
        clients.add(ws)                   # handler(ws, path) with a second arg. Add `path`
        try:                              # to the signature if yours errors on connect.
            await ws.wait_closed()
        finally:
            clients.discard(ws)

    async def stream():
        while True:
            try:
                payload = pipe.compute()
                if payload and clients:
                    msg = json.dumps(payload)
                    await asyncio.gather(*(c.send(msg) for c in list(clients)),
                                         return_exceptions=True)
            except Exception as e:
                print("[warn]", e)
            await asyncio.sleep(args.interval)

    async with websockets.serve(handler, args.host, args.port):
        try:
            await stream()
        finally:
            pipe.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[bye] stopping stream")


# ======================================================================
# WIRING THE FRONT-ENDS  (paste into the HTML files, replacing their sims)
# ======================================================================
#
# --- AURORA (neurofeedback_aurora.html) ---------------------------------
# In frame(), delete the  simulateEEG(dt)  line, and once at startup add:
#
#     const ws = new WebSocket('ws://localhost:8765');
#     ws.onmessage = e => { const d = JSON.parse(e.data);
#                           pushSample({band:d.band, emg:d.emg, ch1:d.ch1, ch2:d.ch2}); };
#
# That's it — the field now responds to your actual band power.
#
# --- SCOPE (spectral_scope.html) ----------------------------------------
# The scope's fitAperiodic()/findPAF() already work on ANY log-power array, so
# feed it the real PSD and let its own math run. Replace synthPSD()'s body with a
# cached copy of the last received spectrum (interpolated onto its F grid), and in
# step() remove the drift(dt) call:
#
#     let lastLogP = null;
#     const ws = new WebSocket('ws://localhost:8765');
#     ws.onmessage = e => { const d = JSON.parse(e.data);
#         // interpolate server freqs/logpsd onto the scope's F[] grid
#         lastLogP = F.map(f => {
#             let i = d.freqs.findIndex(x => x >= f);
#             if (i <= 0) return d.logpsd[0];
#             const t = (f - d.freqs[i-1]) / (d.freqs[i] - d.freqs[i-1]);
#             return d.logpsd[i-1] + t * (d.logpsd[i] - d.logpsd[i-1]); }); };
#     // synthPSD now just returns lastLogP (fall back to a flat line until first msg)
#
# ======================================================================
