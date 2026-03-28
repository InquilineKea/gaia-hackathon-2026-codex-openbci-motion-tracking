#!/usr/bin/env python3
"""
Live GUI plots for FRENZ EEG motor metrics.

Reads rows from the CSV produced by frenz_ble_motor_live.py and updates:
- Motor command
- Alpha/Theta ratio (ATR)
- Peak Alpha Frequency (PAF)
- 1/f falloff
"""

import argparse
import csv
import os
import time
from collections import deque
from datetime import datetime

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation


class CsvTail:
    def __init__(self, path):
        self.path = path
        self.fh = None
        self.header = None
        self.inode = None
        self._open()

    def _open(self):
        if not os.path.exists(self.path):
            self.fh = None
            self.header = None
            self.inode = None
            return
        self.fh = open(self.path, "r", newline="")
        st = os.fstat(self.fh.fileno())
        self.inode = (st.st_dev, st.st_ino)
        header_line = self.fh.readline()
        if not header_line:
            self.header = None
        else:
            hdr = next(csv.reader([header_line]), [])
            self.header = hdr if hdr else None

    def _reopen_if_rotated(self):
        if not os.path.exists(self.path):
            return
        if self.fh is None:
            self._open()
            return
        st = os.stat(self.path)
        inode_now = (st.st_dev, st.st_ino)
        if inode_now != self.inode:
            try:
                self.fh.close()
            except Exception:
                pass
            self._open()

    def read_new_rows(self):
        self._reopen_if_rotated()
        if self.fh is None or self.header is None:
            return []
        rows = []
        while True:
            line = self.fh.readline()
            if not line:
                break
            if line.strip() == "":
                continue
            if line.startswith(self.header[0] + ","):
                # Header repeated after restart/truncate.
                continue
            values = next(csv.reader([line]))
            if len(values) == len(self.header):
                rows.append(dict(zip(self.header, values)))
        return rows


def parse_float(v, default=float("nan")):
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default


def parse_int(v, default=0):
    try:
        if v is None or v == "":
            return default
        return int(float(v))
    except Exception:
        return default


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="/tmp/frenz_ble_motor_metrics.csv")
    ap.add_argument("--points", type=int, default=600)
    ap.add_argument("--interval-ms", type=int, default=250)
    args = ap.parse_args()

    tail = CsvTail(args.csv)

    ts = deque(maxlen=args.points)
    cmd = deque(maxlen=args.points)
    atr = deque(maxlen=args.points)
    paf = deque(maxlen=args.points)
    falloff = deque(maxlen=args.points)
    status = deque(maxlen=args.points)

    plt.style.use("dark_background")
    fig, axes = plt.subplots(4, 1, figsize=(12, 9.5), sharex=True)
    fig.suptitle(
        "Live Brain-to-Motor View (FRENZ EEG Controls Stepper)",
        fontsize=14,
    )
    ax_cmd, ax_atr, ax_paf, ax_fall = axes

    line_cmd, = ax_cmd.plot(
        [], [], lw=1.8, color="#ff8a3d", label="Motor Command (EEG-driven)"
    )
    line_atr, = ax_atr.plot(
        [], [], lw=1.6, color="#4dd2ff", label="Alpha/Theta Ratio (ATR)"
    )
    line_paf, = ax_paf.plot(
        [], [], lw=1.6, color="#9cff57", label="Peak Alpha Frequency (PAF, Hz)"
    )
    line_fall, = ax_fall.plot(
        [], [], lw=1.6, color="#ffd04d", label="1/f Falloff (Aperiodic Slope Proxy)"
    )

    ax_cmd.set_title("Motor Drive: negative=reverse, positive=forward, larger=stronger")
    ax_atr.set_title("Brain State: Alpha/Theta ratio (higher = more alpha-dominant)")
    ax_paf.set_title("Peak Alpha Frequency (within ~8-13 Hz)")
    ax_fall.set_title("1/f Falloff (higher = steeper spectral decay)")

    ax_cmd.set_ylabel("Motor Cmd\n(-rev / +fwd)")
    ax_atr.set_ylabel("ATR\n(alpha/theta)")
    ax_paf.set_ylabel("PAF (Hz)")
    ax_fall.set_ylabel("Falloff")
    ax_fall.set_xlabel("Recent Time (seconds)")

    ax_cmd.set_ylim(-55, 55)
    ax_paf.set_ylim(7.5, 13.5)
    ax_cmd.axhline(0.0, color="white", alpha=0.25, lw=0.9)

    for ax in axes:
        ax.grid(True, alpha=0.25)
        ax.legend(loc="upper left")

    status_text = fig.text(0.01, 0.01, "status=waiting for CSV data", fontsize=10)

    t0 = time.time()

    def update(_frame):
        rows = tail.read_new_rows()
        for r in rows:
            ts.append(parse_float(r.get("unix_ts"), default=time.time()) - t0)
            cmd.append(parse_int(r.get("cmd"), 0))
            atr.append(parse_float(r.get("atr")))
            paf.append(parse_float(r.get("paf_hz")))
            falloff.append(parse_float(r.get("one_over_f_falloff")))
            status.append((r.get("status") or "").strip())

        if len(ts) == 0:
            status_text.set_text(f"status=waiting for CSV data @ {args.csv}")
            return (line_cmd, line_atr, line_paf, line_fall, status_text)

        x = list(ts)
        line_cmd.set_data(x, list(cmd))
        line_atr.set_data(x, list(atr))
        line_paf.set_data(x, list(paf))
        line_fall.set_data(x, list(falloff))

        xmin = max(0.0, x[-1] - 60.0)
        xmax = max(60.0, x[-1])
        for ax in axes:
            ax.set_xlim(xmin, xmax)

        finite_atr = [v for v in atr if v == v]
        finite_fall = [v for v in falloff if v == v]
        if finite_atr:
            lo = min(finite_atr)
            hi = max(finite_atr)
            pad = max(0.2, 0.15 * (hi - lo + 1e-6))
            ax_atr.set_ylim(lo - pad, hi + pad)
        if finite_fall:
            lo = min(finite_fall)
            hi = max(finite_fall)
            pad = max(0.05, 0.15 * (hi - lo + 1e-6))
            ax_fall.set_ylim(lo - pad, hi + pad)

        st = status[-1] if status else "unknown"
        age = (time.time() - (ts[-1] + t0))
        now = datetime.now().strftime("%H:%M:%S")
        status_text.set_text(
            f"time={now}  status={st}  rows={len(ts)}  age={age:.2f}s  csv={args.csv}"
        )
        return (line_cmd, line_atr, line_paf, line_fall, status_text)

    anim = FuncAnimation(
        fig, update, interval=args.interval_ms, blit=False, cache_frame_data=False
    )
    plt.tight_layout(rect=[0, 0.03, 1, 0.96])
    plt.show()
    _ = anim


if __name__ == "__main__":
    main()
