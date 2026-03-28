#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import serial
from scipy import signal, stats


ROOT = Path(__file__).resolve().parent
MPLCONFIGDIR = ROOT / ".mplconfig"
MPLCONFIGDIR.mkdir(exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPLCONFIGDIR))

START_BYTE = 0xA0
STOP_BYTE_MIN = 0xC0
STOP_BYTE_MAX = 0xCF
PACKET_LEN = 33
CYTON_SCALE_UV = 4.5 / 24.0 / (2**23 - 1) * 1_000_000.0


@dataclass
class Metrics:
    wall_time: str
    unix_time: float
    fs_hz: float
    window_seconds: float
    samples: int
    active_channels: list[int]
    paf_hz: float
    delta_power: float
    gamma_power: float
    gamma_delta_ratio: float
    alpha_theta_ratio: float
    one_over_f_slope: float
    one_over_f_exponent: float
    one_over_f_r2: float
    artifact_flag: bool
    artifact_reason: str
    quality: str
    quality_reason: str


def format_metric(value: float, fmt: str) -> str:
    return "nan" if not math.isfinite(value) else format(value, fmt)


def int24_to_int32(raw3: bytes) -> int:
    value = (raw3[0] << 16) | (raw3[1] << 8) | raw3[2]
    if value & 0x800000:
        value -= 1 << 24
    return value


def parse_packet(packet: bytes) -> Optional[np.ndarray]:
    if len(packet) != PACKET_LEN:
        return None
    if packet[0] != START_BYTE or not (STOP_BYTE_MIN <= packet[-1] <= STOP_BYTE_MAX):
        return None

    channels = []
    offset = 2
    for _ in range(8):
        channels.append(int24_to_int32(packet[offset:offset + 3]) * CYTON_SCALE_UV)
        offset += 3
    return np.asarray(channels, dtype=float)


class OpenBCICytonSerialStream:
    def __init__(self, serial_port: str, baud: int, timeout: float) -> None:
        self.serial_port = serial_port
        self.baud = baud
        self.timeout = timeout
        self.ser: Optional[serial.Serial] = None
        self.buffer = bytearray()

    def start(self) -> None:
        self.ser = serial.Serial(self.serial_port, self.baud, timeout=self.timeout)
        time.sleep(1.0)
        self.ser.reset_input_buffer()
        # Try to start binary stream if the board is idle; harmless if already streaming.
        self.ser.write(b"b")
        self.ser.flush()
        time.sleep(0.5)

    def read_packets(self, max_packets: int = 512) -> np.ndarray:
        if self.ser is None:
            return np.empty((0, 8), dtype=float)

        chunk = self.ser.read(4096)
        if chunk:
            self.buffer.extend(chunk)

        packets = []
        while len(packets) < max_packets:
            start_idx = self.buffer.find(bytes([START_BYTE]))
            if start_idx < 0:
                self.buffer.clear()
                break
            if start_idx > 0:
                del self.buffer[:start_idx]
            if len(self.buffer) < PACKET_LEN:
                break
            packet = bytes(self.buffer[:PACKET_LEN])
            parsed = parse_packet(packet)
            del self.buffer[:PACKET_LEN]
            if parsed is not None:
                packets.append(parsed)

        if not packets:
            return np.empty((0, 8), dtype=float)
        return np.vstack(packets)

    def stop(self) -> None:
        if self.ser is not None and self.ser.is_open:
            try:
                self.ser.write(b"s")
                self.ser.flush()
            except Exception:
                pass
            self.ser.close()


def bandpower(freqs: np.ndarray, psd: np.ndarray, low: float, high: float) -> float:
    mask = (freqs >= low) & (freqs <= high)
    if not np.any(mask):
        return float("nan")
    return float(np.trapz(psd[mask], freqs[mask]))


def preprocess_eeg_channel(y: np.ndarray, fs: float) -> np.ndarray:
    y = signal.detrend(np.asarray(y, dtype=float), type="constant")
    b_hp, a_hp = signal.butter(2, 1.0 / (fs / 2.0), btype="highpass")
    y = signal.filtfilt(b_hp, a_hp, y)
    for notch_hz in (60.0, 120.0):
        if notch_hz < fs / 2.0:
            b_notch, a_notch = signal.iirnotch(notch_hz, 30.0, fs)
            y = signal.filtfilt(b_notch, a_notch, y)
    return y


def compute_channel_spectrum(y: np.ndarray, fs: float) -> tuple[np.ndarray, np.ndarray]:
    filtered = preprocess_eeg_channel(y, fs)
    nperseg = min(filtered.size, max(256, int(fs * 4)))
    freqs, psd = signal.welch(filtered, fs=fs, nperseg=nperseg)
    return freqs, psd


def assess_signal_quality(
    paf_hz: float,
    slope: float,
    r2: float,
    chosen_channels: int,
    alpha_theta_ratio: float,
    gamma_delta_ratio: float,
) -> tuple[str, str]:
    realistic_paf = 7.5 <= paf_hz <= 13.5
    realistic_slope = -3.0 <= slope <= -0.2
    gamma_ok = gamma_delta_ratio <= 0.30 or not math.isfinite(gamma_delta_ratio)

    if chosen_channels >= 2 and r2 >= 0.4 and realistic_paf and realistic_slope and gamma_ok:
        return "excellent", "Multiple channels show a plausible alpha peak and a strong 1/f fit."
    if chosen_channels >= 1 and r2 >= 0.2 and realistic_paf and realistic_slope and gamma_ok:
        return "good", "At least one channel shows plausible EEG-like alpha and a usable 1/f fit."
    if chosen_channels >= 1 and realistic_paf:
        return "borderline", "Alpha peak is plausible, but the aperiodic fit is weak or unstable."
    if chosen_channels == 0:
        return "poor", "No non-flat EEG channels survived the quality gate."
    if not gamma_ok:
        return "poor", "Gamma is too elevated relative to delta for a clean resting EEG window."
    if not realistic_paf:
        return "poor", "Peak alpha is outside the typical adult resting range."
    if not realistic_slope:
        return "poor", "The 1/f slope is not in a typical EEG-like range."
    if not math.isfinite(alpha_theta_ratio):
        return "poor", "Alpha/theta ratio could not be computed."
    return "poor", "Signal is too noisy for a confident resting EEG interpretation."


def detect_artifact(gamma_delta_ratio: float, slope: float, r2: float) -> tuple[bool, str]:
    reasons = []
    if math.isfinite(gamma_delta_ratio) and gamma_delta_ratio > 0.30:
        reasons.append("gamma/delta elevated")
    if math.isfinite(slope) and slope > -1.10:
        reasons.append("1/f too flat")
    if math.isfinite(r2) and r2 < 0.40:
        reasons.append("1/f fit weak")
    return bool(reasons), ", ".join(reasons) if reasons else "none"


def compute_metrics(eeg_data: np.ndarray, fs: float, flat_threshold_uv: float, min_r2: float) -> Optional[Metrics]:
    if eeg_data.ndim != 2 or eeg_data.shape[1] < 256:
        return None

    channel_metrics = []
    for idx in range(eeg_data.shape[0]):
        y = np.asarray(eeg_data[idx], dtype=float)
        if np.ptp(y) < flat_threshold_uv:
            continue

        freqs, psd = compute_channel_spectrum(y, fs)
        alpha_mask = (freqs >= 8.0) & (freqs <= 13.0)
        if not np.any(alpha_mask):
            continue

        paf_hz = float(freqs[alpha_mask][np.argmax(psd[alpha_mask])])
        delta_power = bandpower(freqs, psd, 1.0, 4.0)
        gamma_power = bandpower(freqs, psd, 30.0, min(45.0, fs / 2.0 - 1e-6))
        gamma_delta_ratio = float(gamma_power / delta_power) if delta_power > 0 else float("nan")
        alpha_power = bandpower(freqs, psd, 8.0, 13.0)
        theta_power = bandpower(freqs, psd, 4.0, 8.0)
        alpha_theta_ratio = float(alpha_power / theta_power) if theta_power > 0 else float("nan")

        slope_mask = (((freqs >= 2.0) & (freqs < 7.0)) | ((freqs > 14.0) & (freqs <= 40.0)))
        slope_freqs = freqs[slope_mask]
        slope_psd = psd[slope_mask]
        valid = np.isfinite(slope_freqs) & np.isfinite(slope_psd) & (slope_freqs > 0) & (slope_psd > 0)
        slope_freqs = slope_freqs[valid]
        slope_psd = slope_psd[valid]
        if slope_freqs.size < 8:
            continue
        slope, _, r_value, _, _ = stats.linregress(np.log10(slope_freqs), np.log10(slope_psd))
        channel_metrics.append(
            {
                "channel": idx + 1,
                "paf_hz": paf_hz,
                "delta_power": delta_power,
                "gamma_power": gamma_power,
                "gamma_delta_ratio": gamma_delta_ratio,
                "alpha_theta_ratio": alpha_theta_ratio,
                "slope": float(slope),
                "exponent": float(-slope),
                "r2": float(r_value * r_value),
            }
        )

    if not channel_metrics:
        return None

    chosen = [item for item in channel_metrics if item["r2"] >= min_r2] or channel_metrics
    paf = float(np.median([item["paf_hz"] for item in chosen]))
    delta_power = float(np.median([item["delta_power"] for item in chosen]))
    gamma_power = float(np.median([item["gamma_power"] for item in chosen]))
    gamma_delta_ratio = float(np.median([item["gamma_delta_ratio"] for item in chosen]))
    atr = float(np.median([item["alpha_theta_ratio"] for item in chosen]))
    slope = float(np.median([item["slope"] for item in chosen]))
    exponent = float(np.median([item["exponent"] for item in chosen]))
    r2 = float(np.median([item["r2"] for item in chosen]))
    artifact_flag, artifact_reason = detect_artifact(gamma_delta_ratio, slope, r2)
    quality, quality_reason = assess_signal_quality(paf, slope, r2, len(chosen), atr, gamma_delta_ratio)

    return Metrics(
        wall_time=datetime.now().strftime("%H:%M:%S"),
        unix_time=time.time(),
        fs_hz=float(fs),
        window_seconds=float(eeg_data.shape[1] / fs),
        samples=int(eeg_data.shape[1]),
        active_channels=[item["channel"] for item in chosen],
        paf_hz=paf,
        delta_power=delta_power,
        gamma_power=gamma_power,
        gamma_delta_ratio=gamma_delta_ratio,
        alpha_theta_ratio=atr,
        one_over_f_slope=slope,
        one_over_f_exponent=exponent,
        one_over_f_r2=r2,
        artifact_flag=artifact_flag,
        artifact_reason=artifact_reason,
        quality=quality,
        quality_reason=quality_reason,
    )


def build_status_text(metrics: Metrics) -> str:
    channels = ", ".join(str(ch) for ch in metrics.active_channels) or "none"
    return "\n".join(
        [
            "OpenBCI Cyton serial EEG status",
            f"updated_at: {metrics.wall_time}",
            f"window_seconds: {format_metric(metrics.window_seconds, '.1f')}",
            f"sampling_rate_hz: {format_metric(metrics.fs_hz, '.2f')}",
            f"channels_used: {channels}",
            f"peak_alpha_hz: {format_metric(metrics.paf_hz, '.2f')}",
            f"delta_power: {format_metric(metrics.delta_power, '.4f')}",
            f"gamma_power: {format_metric(metrics.gamma_power, '.4f')}",
            f"gamma_delta_ratio: {format_metric(metrics.gamma_delta_ratio, '.4f')}",
            f"alpha_theta_ratio: {format_metric(metrics.alpha_theta_ratio, '.2f')}",
            f"one_over_f_slope: {format_metric(metrics.one_over_f_slope, '.2f')}",
            f"one_over_f_exponent: {format_metric(metrics.one_over_f_exponent, '.2f')}",
            f"one_over_f_r2: {format_metric(metrics.one_over_f_r2, '.2f')}",
            f"artifact_flag: {str(metrics.artifact_flag).lower()}",
            f"artifact_reason: {metrics.artifact_reason}",
            f"signal_quality: {metrics.quality}",
            f"quality_reason: {metrics.quality_reason}",
            "",
        ]
    )


def metric_dict(metrics: Metrics) -> dict[str, object]:
    payload = asdict(metrics)
    for key, value in list(payload.items()):
        if isinstance(value, float) and not math.isfinite(value):
            payload[key] = None
    return payload


def build_spectrum_payload(
    metrics: Metrics,
    eeg_data: np.ndarray,
    fs: float,
    max_points: int = 256,
) -> dict[str, object]:
    if eeg_data.ndim != 2 or eeg_data.shape[1] < 256:
        return {
            "channels": [],
            "frequencies_hz": [],
            "median_psd": [],
            "psd_by_channel": {},
        }

    chosen_indices = [ch - 1 for ch in metrics.active_channels if 1 <= ch <= eeg_data.shape[0]]
    if not chosen_indices:
        chosen_indices = list(range(eeg_data.shape[0]))

    freq_axis = None
    per_channel: dict[str, np.ndarray] = {}
    for idx in chosen_indices:
        y = np.asarray(eeg_data[idx], dtype=float)
        if np.ptp(y) < 1e-9:
            continue
        freqs, psd = compute_channel_spectrum(y, fs)
        mask = (freqs >= 1.0) & (freqs <= min(45.0, fs / 2.0 - 1e-6))
        if not np.any(mask):
            continue
        masked_freqs = freqs[mask]
        masked_psd = psd[mask]
        if freq_axis is None:
            freq_axis = masked_freqs
        if freq_axis.shape != masked_freqs.shape or not np.allclose(freq_axis, masked_freqs):
            continue
        per_channel[f"ch{idx + 1}"] = masked_psd

    if not per_channel or freq_axis is None:
        return {
            "channels": [],
            "frequencies_hz": [],
            "median_psd": [],
            "psd_by_channel": {},
        }

    stride = max(1, int(math.ceil(freq_axis.size / max_points)))
    reduced_freqs = freq_axis[::stride]
    reduced_channel = {key: value[::stride] for key, value in per_channel.items()}
    stacked = np.vstack([value for value in reduced_channel.values()])
    median_psd = np.median(stacked, axis=0)

    return {
        "channels": [int(key[2:]) for key in reduced_channel.keys()],
        "frequencies_hz": [round(float(value), 3) for value in reduced_freqs.tolist()],
        "median_psd": [round(float(value), 6) for value in median_psd.tolist()],
        "psd_by_channel": {
            key: [round(float(value), 6) for value in values.tolist()]
            for key, values in reduced_channel.items()
        },
    }


def build_live_payload(
    metrics: Metrics,
    eeg_data: np.ndarray,
    fs: float,
    max_points: int = 1200,
) -> dict[str, object]:
    if eeg_data.ndim != 2 or eeg_data.shape[1] == 0:
        channels: dict[str, list[float]] = {}
        time_axis: list[float] = []
        source_samples = 0
        returned_samples = 0
        stride = 1
    else:
        source_samples = int(eeg_data.shape[1])
        stride = max(1, int(math.ceil(source_samples / max_points)))
        downsampled = eeg_data[:, ::stride]
        returned_samples = int(downsampled.shape[1])
        time_axis = [round(float(value), 3) for value in ((np.arange(returned_samples) * stride) - (source_samples - 1)) / fs]
        channels = {
            f"ch{idx + 1}": [round(float(value), 3) for value in downsampled[idx].tolist()]
            for idx in range(downsampled.shape[0])
        }

    return {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "status_text": build_status_text(metrics),
        "metrics": metric_dict(metrics),
        "spectrum": build_spectrum_payload(metrics, eeg_data, fs),
        "stream": {
            "fs_hz": round(float(fs), 3),
            "window_seconds": round(float(source_samples / fs), 3) if fs > 0 else None,
            "source_samples": source_samples,
            "returned_samples": returned_samples,
            "downsample_stride": stride,
            "time_axis_seconds": time_axis,
            "eeg_uv": channels,
        },
    }


def summarize_history(history: list[Metrics]) -> str:
    if not history:
        return "No valid metrics were captured.\n"

    pafs = np.array([m.paf_hz for m in history], dtype=float)
    deltas = np.array([m.delta_power for m in history], dtype=float)
    gammas = np.array([m.gamma_power for m in history], dtype=float)
    gdrs = np.array([m.gamma_delta_ratio for m in history], dtype=float)
    slopes = np.array([m.one_over_f_slope for m in history], dtype=float)
    r2s = np.array([m.one_over_f_r2 for m in history], dtype=float)
    atrs = np.array([m.alpha_theta_ratio for m in history], dtype=float)
    last = history[-1]
    overall_quality, overall_reason = assess_signal_quality(
        paf_hz=float(np.nanmedian(pafs)),
        slope=float(np.nanmedian(slopes)),
        r2=float(np.nanmedian(r2s)),
        chosen_channels=max(len(m.active_channels) for m in history),
        alpha_theta_ratio=float(np.nanmedian(atrs)),
        gamma_delta_ratio=float(np.nanmedian(gdrs)),
    )
    return "\n".join(
        [
            "OpenBCI Cyton serial EEG summary",
            f"ended_at: {datetime.now().strftime('%H:%M:%S')}",
            f"updates_captured: {len(history)}",
            f"last_paf_hz: {format_metric(last.paf_hz, '.2f')}",
            f"median_paf_hz: {format_metric(float(np.nanmedian(pafs)), '.2f')}",
            f"median_delta_power: {format_metric(float(np.nanmedian(deltas)), '.4f')}",
            f"median_gamma_power: {format_metric(float(np.nanmedian(gammas)), '.4f')}",
            f"median_gamma_delta_ratio: {format_metric(float(np.nanmedian(gdrs)), '.4f')}",
            f"median_alpha_theta_ratio: {format_metric(float(np.nanmedian(atrs)), '.2f')}",
            f"median_one_over_f_slope: {format_metric(float(np.nanmedian(slopes)), '.2f')}",
            f"median_one_over_f_r2: {format_metric(float(np.nanmedian(r2s)), '.2f')}",
            f"last_artifact_flag: {str(last.artifact_flag).lower()}",
            f"last_artifact_reason: {last.artifact_reason}",
            f"last_quality: {last.quality}",
            f"overall_quality: {overall_quality}",
            f"overall_reason: {overall_reason}",
            "",
        ]
    )


def print_metrics(metrics: Metrics, as_json: bool) -> None:
    if as_json:
        print(json.dumps(asdict(metrics), separators=(",", ":")))
        return
    channels = ",".join(str(ch) for ch in metrics.active_channels)
    print(
        f"{metrics.wall_time} "
        f"fs={format_metric(metrics.fs_hz, '.2f')}Hz "
        f"win={format_metric(metrics.window_seconds, '.1f')}s "
        f"ch=[{channels}] "
        f"PAF={format_metric(metrics.paf_hz, '.2f')}Hz "
        f"D={format_metric(metrics.delta_power, '.4f')} "
        f"G={format_metric(metrics.gamma_power, '.4f')} "
        f"G/D={format_metric(metrics.gamma_delta_ratio, '.4f')} "
        f"A/T={format_metric(metrics.alpha_theta_ratio, '.2f')} "
        f"1/f slope={format_metric(metrics.one_over_f_slope, '.2f')} "
        f"exp={format_metric(metrics.one_over_f_exponent, '.2f')} "
        f"r2={format_metric(metrics.one_over_f_r2, '.2f')} "
        f"artifact={'yes' if metrics.artifact_flag else 'no'} "
        f"quality={metrics.quality}",
        flush=True,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Direct serial PAF and 1/f metrics for OpenBCI Cyton packets.")
    parser.add_argument("--serial-port", default="/dev/cu.usbserial-DN00954N")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--fs", type=float, default=250.0)
    parser.add_argument("--window-sec", type=float, default=10.0)
    parser.add_argument("--duration-sec", type=float, default=20.0)
    parser.add_argument("--update-sec", type=float, default=1.0)
    parser.add_argument("--flat-threshold-uv", type=float, default=5.0)
    parser.add_argument("--min-r2", type=float, default=0.2)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--status-path", type=Path)
    parser.add_argument("--payload-path", type=Path)
    parser.add_argument("--summary-path", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    stream = OpenBCICytonSerialStream(args.serial_port, args.baud, timeout=0.5)
    history: list[Metrics] = []
    eeg_buffer = np.empty((8, 0), dtype=float)
    needed_samples = max(256, int(round(args.window_sec * args.fs)))
    last_emit = 0.0

    try:
        stream.start()
        started = time.monotonic()
        while True:
            packets = stream.read_packets()
            if packets.size > 0:
                eeg_buffer = np.hstack([eeg_buffer, packets.T])
                if eeg_buffer.shape[1] > needed_samples:
                    eeg_buffer = eeg_buffer[:, -needed_samples:]

            now = time.monotonic()
            if now - last_emit >= args.update_sec:
                metrics = compute_metrics(
                    eeg_data=eeg_buffer,
                    fs=args.fs,
                    flat_threshold_uv=args.flat_threshold_uv,
                    min_r2=args.min_r2,
                )
                if metrics is not None:
                    history.append(metrics)
                    print_metrics(metrics, as_json=args.json)
                    if args.status_path is not None:
                        args.status_path.write_text(build_status_text(metrics))
                    if args.payload_path is not None:
                        args.payload_path.write_text(json.dumps(build_live_payload(metrics, eeg_buffer, args.fs), indent=2))
                last_emit = now

            if args.duration_sec > 0 and (now - started) >= args.duration_sec:
                break

    finally:
        if args.summary_path is not None:
            args.summary_path.write_text(summarize_history(history))
        stream.stop()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
