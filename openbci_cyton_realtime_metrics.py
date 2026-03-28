#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
from brainflow.board_shim import BoardIds, BoardShim, BrainFlowInputParams, LogLevels
from scipy import signal, stats


ROOT = Path(__file__).resolve().parent
MPLCONFIGDIR = ROOT / ".mplconfig"
MPLCONFIGDIR.mkdir(exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPLCONFIGDIR))


@dataclass
class Metrics:
    wall_time: str
    unix_time: float
    fs_hz: float
    window_seconds: float
    samples: int
    active_channels: list[int]
    paf_hz: float
    alpha_theta_ratio: float
    one_over_f_slope: float
    one_over_f_exponent: float
    one_over_f_r2: float
    quality: str
    quality_reason: str


def format_metric(value: float, fmt: str) -> str:
    return "nan" if not math.isfinite(value) else format(value, fmt)


def bandpower(freqs: np.ndarray, psd: np.ndarray, low: float, high: float) -> float:
    mask = (freqs >= low) & (freqs <= high)
    if not np.any(mask):
        return float("nan")
    return float(np.trapz(psd[mask], freqs[mask]))


def assess_signal_quality(
    paf_hz: float,
    slope: float,
    r2: float,
    chosen_channels: int,
    alpha_theta_ratio: float,
) -> tuple[str, str]:
    realistic_paf = 7.5 <= paf_hz <= 13.5
    realistic_slope = -3.0 <= slope <= -0.2

    if chosen_channels >= 2 and r2 >= 0.4 and realistic_paf and realistic_slope:
        return "excellent", "Multiple channels show a plausible alpha peak and a strong 1/f fit."
    if chosen_channels >= 1 and r2 >= 0.2 and realistic_paf and realistic_slope:
        return "good", "At least one channel shows plausible EEG-like alpha and a usable 1/f fit."
    if chosen_channels >= 1 and realistic_paf:
        return "borderline", "Alpha peak is plausible, but the aperiodic fit is weak or unstable."
    if chosen_channels == 0:
        return "poor", "No non-flat EEG channels survived the quality gate."
    if not realistic_paf:
        return "poor", "Peak alpha is outside the typical adult resting range."
    if not realistic_slope:
        return "poor", "The 1/f slope is not in a typical EEG-like range."
    if not math.isfinite(alpha_theta_ratio):
        return "poor", "Alpha/theta ratio could not be computed."
    return "poor", "Signal is too noisy for a confident resting EEG interpretation."


def compute_metrics(
    eeg_data: np.ndarray,
    fs: float,
    flat_threshold_uv: float,
    min_r2: float,
) -> Optional[Metrics]:
    if eeg_data.ndim != 2 or eeg_data.shape[1] < 256:
        return None

    channel_metrics = []
    for idx in range(eeg_data.shape[0]):
        y = np.asarray(eeg_data[idx], dtype=float)
        if np.ptp(y) < flat_threshold_uv:
            continue

        y = signal.detrend(y, type="constant")
        b_hp, a_hp = signal.butter(2, 1.0 / (fs / 2.0), btype="highpass")
        y = signal.filtfilt(b_hp, a_hp, y)

        for notch_hz in (60.0, 120.0):
            if notch_hz < fs / 2.0:
                b_notch, a_notch = signal.iirnotch(notch_hz, 30.0, fs)
                y = signal.filtfilt(b_notch, a_notch, y)

        nperseg = min(y.size, max(256, int(fs * 4)))
        freqs, psd = signal.welch(y, fs=fs, nperseg=nperseg)

        alpha_mask = (freqs >= 8.0) & (freqs <= 13.0)
        if not np.any(alpha_mask):
            continue

        alpha_freqs = freqs[alpha_mask]
        alpha_psd = psd[alpha_mask]
        paf_hz = float(alpha_freqs[np.argmax(alpha_psd)])
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
                "alpha_theta_ratio": alpha_theta_ratio,
                "slope": float(slope),
                "exponent": float(-slope),
                "r2": float(r_value * r_value),
            }
        )

    if not channel_metrics:
        return None

    good_channels = [item for item in channel_metrics if item["r2"] >= min_r2]
    chosen = good_channels or channel_metrics

    paf = float(np.median([item["paf_hz"] for item in chosen]))
    atr = float(np.median([item["alpha_theta_ratio"] for item in chosen]))
    slope = float(np.median([item["slope"] for item in chosen]))
    exponent = float(np.median([item["exponent"] for item in chosen]))
    r2 = float(np.median([item["r2"] for item in chosen]))
    quality, quality_reason = assess_signal_quality(
        paf_hz=paf,
        slope=slope,
        r2=r2,
        chosen_channels=len(chosen),
        alpha_theta_ratio=atr,
    )

    return Metrics(
        wall_time=datetime.now().strftime("%H:%M:%S"),
        unix_time=time.time(),
        fs_hz=float(fs),
        window_seconds=float(eeg_data.shape[1] / fs),
        samples=int(eeg_data.shape[1]),
        active_channels=[item["channel"] for item in chosen],
        paf_hz=paf,
        alpha_theta_ratio=atr,
        one_over_f_slope=slope,
        one_over_f_exponent=exponent,
        one_over_f_r2=r2,
        quality=quality,
        quality_reason=quality_reason,
    )


def build_status_text(metrics: Metrics) -> str:
    channels = ", ".join(str(ch) for ch in metrics.active_channels) or "none"
    return "\n".join(
        [
            "OpenBCI Cyton live EEG status",
            f"updated_at: {metrics.wall_time}",
            f"window_seconds: {format_metric(metrics.window_seconds, '.1f')}",
            f"sampling_rate_hz: {format_metric(metrics.fs_hz, '.2f')}",
            f"channels_used: {channels}",
            f"peak_alpha_hz: {format_metric(metrics.paf_hz, '.2f')}",
            f"alpha_theta_ratio: {format_metric(metrics.alpha_theta_ratio, '.2f')}",
            f"one_over_f_slope: {format_metric(metrics.one_over_f_slope, '.2f')}",
            f"one_over_f_exponent: {format_metric(metrics.one_over_f_exponent, '.2f')}",
            f"one_over_f_r2: {format_metric(metrics.one_over_f_r2, '.2f')}",
            f"signal_quality: {metrics.quality}",
            f"quality_reason: {metrics.quality_reason}",
            "",
        ]
    )


def summarize_history(history: list[Metrics]) -> str:
    if not history:
        return "No valid metrics were captured.\n"

    pafs = np.array([m.paf_hz for m in history], dtype=float)
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
    )

    return "\n".join(
        [
            "OpenBCI Cyton live EEG summary",
            f"ended_at: {datetime.now().strftime('%H:%M:%S')}",
            f"updates_captured: {len(history)}",
            f"last_paf_hz: {format_metric(last.paf_hz, '.2f')}",
            f"median_paf_hz: {format_metric(float(np.nanmedian(pafs)), '.2f')}",
            f"median_alpha_theta_ratio: {format_metric(float(np.nanmedian(atrs)), '.2f')}",
            f"median_one_over_f_slope: {format_metric(float(np.nanmedian(slopes)), '.2f')}",
            f"median_one_over_f_r2: {format_metric(float(np.nanmedian(r2s)), '.2f')}",
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
        f"A/T={format_metric(metrics.alpha_theta_ratio, '.2f')} "
        f"1/f slope={format_metric(metrics.one_over_f_slope, '.2f')} "
        f"exp={format_metric(metrics.one_over_f_exponent, '.2f')} "
        f"r2={format_metric(metrics.one_over_f_r2, '.2f')} "
        f"quality={metrics.quality}",
        flush=True,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Real-time PAF and 1/f metrics for OpenBCI Cyton via BrainFlow.")
    parser.add_argument("--serial-port", default="/dev/cu.usbserial-DN00954N")
    parser.add_argument("--board-id", type=int, default=BoardIds.CYTON_BOARD.value)
    parser.add_argument("--window-sec", type=float, default=20.0)
    parser.add_argument("--update-sec", type=float, default=1.0)
    parser.add_argument("--duration-sec", type=float, default=0.0)
    parser.add_argument("--startup-sec", type=float, default=4.0)
    parser.add_argument("--flat-threshold-uv", type=float, default=5.0)
    parser.add_argument("--min-r2", type=float, default=0.2)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--status-path", type=Path)
    parser.add_argument("--summary-path", type=Path)
    parser.add_argument("--streamer-params", default="")
    parser.add_argument("--gain-command", default="", help="Optional command to send after connect, e.g. /0 for defaults.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    BoardShim.enable_dev_board_logger()

    params = BrainFlowInputParams()
    params.serial_port = args.serial_port
    params.ip_port = 0
    params.serial_number = ""
    params.other_info = ""
    params.mac_address = ""
    params.ip_address = ""
    params.ip_protocol = 0
    params.timeout = 15
    params.file = ""
    params.master_board = BoardIds.NO_BOARD.value

    board = BoardShim(args.board_id, params)
    history: list[Metrics] = []

    try:
        board.prepare_session()
        board.start_stream(45000, args.streamer_params)
        if args.gain_command:
            board.config_board(args.gain_command)
        time.sleep(args.startup_sec)

        fs = BoardShim.get_sampling_rate(args.board_id)
        eeg_channels = BoardShim.get_eeg_channels(args.board_id)
        needed_samples = max(256, int(round(args.window_sec * fs)))
        last_emit = 0.0
        started = time.monotonic()

        while True:
            now = time.monotonic()
            if now - last_emit >= args.update_sec:
                data = board.get_current_board_data(needed_samples)
                if data.size > 0:
                    eeg_data = data[eeg_channels, :]
                    metrics = compute_metrics(
                        eeg_data=eeg_data,
                        fs=fs,
                        flat_threshold_uv=args.flat_threshold_uv,
                        min_r2=args.min_r2,
                    )
                    if metrics is not None:
                        history.append(metrics)
                        print_metrics(metrics, as_json=args.json)
                        if args.status_path is not None:
                            args.status_path.write_text(build_status_text(metrics))
                last_emit = now

            if args.duration_sec > 0 and (now - started) >= args.duration_sec:
                break

            time.sleep(0.05)

    finally:
        if args.summary_path is not None:
            args.summary_path.write_text(summarize_history(history))
        try:
            board.stop_stream()
        except Exception:
            pass
        try:
            board.release_session()
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
