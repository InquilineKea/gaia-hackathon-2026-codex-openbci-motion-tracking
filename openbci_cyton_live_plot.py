#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation
from scipy import signal

from openbci_cyton_serial_metrics import (
    OpenBCICytonSerialStream,
    build_live_payload,
    build_status_text,
    compute_metrics,
    format_metric,
    summarize_history,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Real-time scrolling OpenBCI Cyton plot with live PAF, alpha/theta, gamma/delta, and 1/f."
    )
    parser.add_argument("--serial-port", default="/dev/cu.usbserial-DN00954N")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--fs", type=float, default=250.0)
    parser.add_argument("--window-sec", type=float, default=20.0)
    parser.add_argument("--plot-sec", type=float, default=8.0)
    parser.add_argument("--interval-ms", type=int, default=250)
    parser.add_argument("--display-channels", default="2,7")
    parser.add_argument("--flat-threshold-uv", type=float, default=5.0)
    parser.add_argument("--min-r2", type=float, default=0.2)
    parser.add_argument("--figure-width", type=float, default=14.0)
    parser.add_argument("--figure-height", type=float, default=8.0)
    parser.add_argument("--metrics-font-size", type=float, default=8.5)
    parser.add_argument("--title-font-size", type=float, default=11.0)
    parser.add_argument("--label-font-size", type=float, default=8.5)
    parser.add_argument("--tick-font-size", type=float, default=7.5)
    parser.add_argument("--legend-font-size", type=float, default=7.5)
    parser.add_argument("--band-history-sec", type=float, default=120.0)
    parser.add_argument("--status-path", type=Path)
    parser.add_argument("--payload-path", type=Path)
    parser.add_argument("--summary-path", type=Path)
    return parser.parse_args()


class CytonLivePlot:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.stream = OpenBCICytonSerialStream(args.serial_port, args.baud, timeout=0.5)
        self.history = []
        self.band_history = []
        self.started_monotonic = time.monotonic()
        self.eeg_buffer = np.empty((8, 0), dtype=float)
        self.window_samples = max(256, int(round(args.window_sec * args.fs)))
        self.plot_samples = max(256, int(round(args.plot_sec * args.fs)))
        self.display_channels = [max(1, int(ch.strip())) for ch in args.display_channels.split(",") if ch.strip()]
        self.display_indices = [ch - 1 for ch in self.display_channels if 1 <= ch <= 8]

        self.fig = plt.figure(figsize=(args.figure_width, args.figure_height))
        gs = self.fig.add_gridspec(2, 2, width_ratios=[3.3, 1.4], height_ratios=[1.5, 1.0])
        self.ax_time = self.fig.add_subplot(gs[0, :])
        self.ax_psd = self.fig.add_subplot(gs[1, 0])
        right_gs = gs[1, 1].subgridspec(2, 1, height_ratios=[1.55, 1.0], hspace=0.25)
        self.ax_text = self.fig.add_subplot(right_gs[0, 0])
        self.ax_bands = self.fig.add_subplot(right_gs[1, 0])
        self.ax_text.axis("off")

        self.time_lines = []
        colors = ["tab:blue", "tab:red", "tab:green", "tab:purple", "tab:orange", "tab:brown", "tab:pink", "tab:gray"]
        for idx, ch in enumerate(self.display_channels):
            line, = self.ax_time.plot([], [], lw=1.2, color=colors[idx % len(colors)], label=f"Ch {ch}")
            self.time_lines.append(line)

        self.psd_lines = []
        for idx, ch in enumerate(self.display_channels):
            line, = self.ax_psd.semilogy([], [], lw=1.2, color=colors[idx % len(colors)], label=f"Ch {ch}")
            self.psd_lines.append(line)

        self.metrics_text = self.ax_text.text(
            0.0,
            1.0,
            "Waiting for Cyton data...",
            va="top",
            ha="left",
            family="monospace",
            fontsize=args.metrics_font_size,
            linespacing=1.0,
        )

        self.ax_time.set_title("OpenBCI Cyton Real-Time EEG", fontsize=args.title_font_size)
        self.ax_time.set_xlabel("Time (s)", fontsize=args.label_font_size)
        self.ax_time.set_ylabel("Amplitude (stacked uV)", fontsize=args.label_font_size)
        self.ax_time.grid(True, alpha=0.2)
        self.ax_time.tick_params(labelsize=args.tick_font_size)
        self.ax_time.legend(
            loc="upper right",
            ncol=max(1, min(4, len(self.display_channels))),
            fontsize=args.legend_font_size,
        )

        self.ax_psd.set_title("Power Spectral Density", fontsize=args.title_font_size)
        self.ax_psd.set_xlabel("Frequency (Hz)", fontsize=args.label_font_size)
        self.ax_psd.set_ylabel("Power", fontsize=args.label_font_size)
        self.ax_psd.set_xlim(1, 45)
        self.ax_psd.grid(True, alpha=0.2)
        self.ax_psd.tick_params(labelsize=args.tick_font_size)
        self.ax_psd.legend(loc="upper right", fontsize=args.legend_font_size)
        self.ax_psd.axvspan(1, 4, alpha=0.07, color="gray")
        self.ax_psd.axvspan(4, 8, alpha=0.07, color="cyan")
        self.ax_psd.axvspan(8, 13, alpha=0.10, color="green")
        self.ax_psd.axvspan(30, 45, alpha=0.05, color="orange")

        self.band_lines = {}
        self.band_specs = {
            "delta": ("Delta", "tab:gray"),
            "alpha": ("Alpha", "tab:green"),
            "beta": ("Beta", "tab:orange"),
            "gamma": ("Gamma", "tab:red"),
        }
        for key, (label, color) in self.band_specs.items():
            line, = self.ax_bands.plot([], [], lw=1.4, color=color, label=label)
            self.band_lines[key] = line
        self.ax_bands.set_title("Band Power", fontsize=args.title_font_size)
        self.ax_bands.set_xlabel("Time (s)", fontsize=args.label_font_size)
        self.ax_bands.set_ylabel("Power", fontsize=args.label_font_size)
        self.ax_bands.tick_params(labelsize=args.tick_font_size)
        self.ax_bands.grid(True, alpha=0.2)
        self.ax_bands.legend(loc="upper right", ncol=2, fontsize=args.legend_font_size)

        self.fig.tight_layout()

    @staticmethod
    def _bandpower_from_spectrum(freqs: np.ndarray, psd: np.ndarray, low: float, high: float) -> float:
        mask = (freqs >= low) & (freqs <= high)
        if not np.any(mask):
            return float("nan")
        return float(np.trapz(psd[mask], freqs[mask]))

    def _render_band_powers(self, payload: dict) -> None:
        spectrum = payload.get("spectrum") or {}
        freqs = np.asarray(spectrum.get("frequencies_hz") or [], dtype=float)
        median_psd = np.asarray(spectrum.get("median_psd") or [], dtype=float)
        if freqs.size < 4 or median_psd.size != freqs.size:
            return

        elapsed = time.monotonic() - self.started_monotonic
        band_values = {
            "delta": self._bandpower_from_spectrum(freqs, median_psd, 1.0, 4.0),
            "alpha": self._bandpower_from_spectrum(freqs, median_psd, 8.0, 13.0),
            "beta": self._bandpower_from_spectrum(freqs, median_psd, 13.0, 30.0),
            "gamma": self._bandpower_from_spectrum(freqs, median_psd, 30.0, 45.0),
        }
        self.band_history.append({"t": elapsed, **band_values})
        min_t = elapsed - self.args.band_history_sec
        self.band_history = [item for item in self.band_history if item["t"] >= min_t]

        times = np.asarray([item["t"] - elapsed for item in self.band_history], dtype=float)
        all_values = []
        for key, line in self.band_lines.items():
            values = np.asarray([item[key] for item in self.band_history], dtype=float)
            values = np.where(np.isfinite(values), np.maximum(values, 1e-6), np.nan)
            line.set_data(times, values)
            all_values.append(values[np.isfinite(values)])

        self.ax_bands.set_xlim(max(-self.args.band_history_sec, times[0] if times.size else -self.args.band_history_sec), 0.0)
        finite_values = np.concatenate([values for values in all_values if values.size > 0]) if all_values else np.array([])
        if finite_values.size > 0:
            ymin = float(np.nanmin(finite_values))
            ymax = float(np.nanmax(finite_values))
            if ymax > ymin:
                pad = (ymax - ymin) * 0.12
                self.ax_bands.set_ylim(max(0.0, ymin - pad), ymax + pad)
            else:
                self.ax_bands.set_ylim(max(0.0, ymin * 0.9), ymax * 1.1 + 1e-6)

    def _update_buffers(self) -> None:
        packets = self.stream.read_packets()
        if packets.size == 0:
            return
        self.eeg_buffer = np.hstack([self.eeg_buffer, packets.T])
        if self.eeg_buffer.shape[1] > self.window_samples:
            self.eeg_buffer = self.eeg_buffer[:, -self.window_samples:]

    def _render_time_series(self) -> None:
        if self.eeg_buffer.shape[1] == 0:
            return

        data = self.eeg_buffer[:, -min(self.plot_samples, self.eeg_buffer.shape[1]):]
        t = np.arange(data.shape[1]) / self.args.fs
        t = t - t[-1]

        view = data[self.display_indices, :]
        centered = view - np.nanmedian(view, axis=1, keepdims=True)
        channel_spread = np.nanpercentile(np.abs(centered), 95, axis=1)
        spacing = max(50.0, float(np.nanmax(channel_spread) * 2.5))

        for idx, line in enumerate(self.time_lines):
            y = centered[idx] + (len(self.time_lines) - 1 - idx) * spacing
            line.set_data(t, y)

        ymin = -spacing
        ymax = len(self.time_lines) * spacing
        self.ax_time.set_xlim(t[0], 0.0)
        self.ax_time.set_ylim(ymin, ymax)

    def _render_psd(self) -> None:
        if self.eeg_buffer.shape[1] < 256:
            return

        view = self.eeg_buffer[self.display_indices, :]
        for idx, line in enumerate(self.psd_lines):
            y = signal.detrend(view[idx], type="constant")
            b_hp, a_hp = signal.butter(2, 1.0 / (self.args.fs / 2.0), btype="highpass")
            y = signal.filtfilt(b_hp, a_hp, y)
            for notch_hz in (60.0, 120.0):
                if notch_hz < self.args.fs / 2.0:
                    b_notch, a_notch = signal.iirnotch(notch_hz, 30.0, self.args.fs)
                    y = signal.filtfilt(b_notch, a_notch, y)
            nperseg = min(y.size, max(256, int(self.args.fs * 4)))
            freqs, psd = signal.welch(y, fs=self.args.fs, nperseg=nperseg)
            mask = (freqs >= 1.0) & (freqs <= 45.0)
            line.set_data(freqs[mask], psd[mask])

        self.ax_psd.relim()
        self.ax_psd.autoscale_view(scalex=False, scaley=True)

    def _render_metrics(self) -> None:
        metrics = compute_metrics(
            eeg_data=self.eeg_buffer,
            fs=self.args.fs,
            flat_threshold_uv=self.args.flat_threshold_uv,
            min_r2=self.args.min_r2,
        )
        if metrics is None:
            self.metrics_text.set_text("Waiting for enough clean data...")
            return

        self.history.append(metrics)
        payload = build_live_payload(metrics, self.eeg_buffer, self.args.fs)
        if self.args.status_path is not None:
            self.args.status_path.write_text(build_status_text(metrics))
        if self.args.payload_path is not None:
            self.args.payload_path.write_text(json.dumps(payload, indent=2))
        self._render_band_powers(payload)

        lines = [
            f"time        {metrics.wall_time}",
            f"channels    {','.join(str(ch) for ch in metrics.active_channels)}",
            f"PAF         {format_metric(metrics.paf_hz, '.2f')} Hz",
            f"alpha/theta {format_metric(metrics.alpha_theta_ratio, '.2f')}",
            f"gamma/delta {format_metric(metrics.gamma_delta_ratio, '.4f')}",
            f"1/f slope   {format_metric(metrics.one_over_f_slope, '.2f')}",
            f"1/f exp     {format_metric(metrics.one_over_f_exponent, '.2f')}",
            f"1/f r2      {format_metric(metrics.one_over_f_r2, '.2f')}",
            f"artifact    {'YES' if metrics.artifact_flag else 'NO'}",
            f"artifact why {metrics.artifact_reason}",
            f"quality     {metrics.quality}",
            "",
            metrics.quality_reason,
        ]
        self.metrics_text.set_text("\n".join(lines))
        self.fig.suptitle(
            f"Cyton live  PAF {format_metric(metrics.paf_hz, '.2f')} Hz  "
            f"A/T {format_metric(metrics.alpha_theta_ratio, '.2f')}  "
            f"G/D {format_metric(metrics.gamma_delta_ratio, '.4f')}  "
            f"artifact {'YES' if metrics.artifact_flag else 'NO'}",
            fontsize=self.args.title_font_size,
        )

    def update(self, _frame):
        self._update_buffers()
        self._render_time_series()
        self._render_psd()
        self._render_metrics()
        return [*self.time_lines, *self.psd_lines, *self.band_lines.values(), self.metrics_text]

    def run(self) -> None:
        self.stream.start()
        self.ani = FuncAnimation(
            self.fig,
            self.update,
            interval=self.args.interval_ms,
            blit=False,
            cache_frame_data=False,
        )
        try:
            plt.show()
        finally:
            if self.args.summary_path is not None:
                self.args.summary_path.write_text(summarize_history(self.history))
            self.stream.stop()


def main() -> int:
    args = parse_args()
    app = CytonLivePlot(args)
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
