#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

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
        description="Real-time OpenBCI Cyton analyzer for PAF, alpha/theta, gamma/delta, and 1/f."
    )
    parser.add_argument("--serial-port", default="/dev/cu.usbserial-DN00954N")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--fs", type=float, default=250.0)
    parser.add_argument("--window-sec", type=float, default=20.0)
    parser.add_argument("--duration-sec", type=float, default=0.0, help="0 means run until Ctrl-C.")
    parser.add_argument("--update-sec", type=float, default=1.0)
    parser.add_argument("--flat-threshold-uv", type=float, default=5.0)
    parser.add_argument("--min-r2", type=float, default=0.2)
    parser.add_argument("--status-path", type=Path)
    parser.add_argument("--payload-path", type=Path)
    parser.add_argument("--summary-path", type=Path)
    return parser.parse_args()


def print_realtime(metrics) -> None:
    channels = ",".join(str(ch) for ch in metrics.active_channels)
    print(
        f"{metrics.wall_time} "
        f"ch=[{channels}] "
        f"PAF={format_metric(metrics.paf_hz, '.2f')}Hz "
        f"A/T={format_metric(metrics.alpha_theta_ratio, '.2f')} "
        f"G/D={format_metric(metrics.gamma_delta_ratio, '.4f')} "
        f"1/f={format_metric(metrics.one_over_f_slope, '.2f')} "
        f"r2={format_metric(metrics.one_over_f_r2, '.2f')} "
        f"artifact={'yes' if metrics.artifact_flag else 'no'} "
        f"quality={metrics.quality}",
        flush=True,
    )


def main() -> int:
    args = parse_args()
    stream = OpenBCICytonSerialStream(args.serial_port, args.baud, timeout=0.5)
    history = []
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
                    print_realtime(metrics)
                    if args.status_path is not None:
                        args.status_path.write_text(build_status_text(metrics))
                    if args.payload_path is not None:
                        args.payload_path.write_text(json.dumps(build_live_payload(metrics, eeg_buffer, args.fs), indent=2))
                last_emit = now

            if args.duration_sec > 0 and (now - started) >= args.duration_sec:
                break

            time.sleep(0.05)

    except KeyboardInterrupt:
        pass
    finally:
        if args.summary_path is not None:
            args.summary_path.write_text(summarize_history(history))
        stream.stop()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
