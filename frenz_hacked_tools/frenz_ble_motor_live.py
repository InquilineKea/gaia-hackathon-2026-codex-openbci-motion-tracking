#!/usr/bin/env python3
"""
Live FRENZ BLE -> Arduino stepper control.

- No repeating synthetic pattern.
- Motor command comes from real-time EEG ATR trend.
- Sends motor stop (0) when EEG stream times out/stops.
"""

import argparse
import asyncio
import csv
import math
import os
import signal
import sys
import time
from collections import deque
from datetime import datetime, timezone

import numpy as np
import serial
from bleak import BleakClient, BleakScanner
from scipy import signal as spsig


DEVICE_NAME_DEFAULT = "FRENZL70"

# FRENZ UUIDs (reverse engineered from existing scripts)
CMD_RX_UUID = "45420101-0000-ffff-ff45-415241424c45"
CMD_RES_UUID = "45420102-0000-ffff-ff45-415241424c45"
EEG_STREAM_UUID = "45420201-0000-ffff-ff45-415241424c45"

CMD_ON_CONNECTED = b"\x0e\x00"
CMD_OFF_CONNECTED = b"\x0e\x01"
CMD_DATA_STREAM_CTRL = b"\x03"
CMD_START_NOTIFY_DATA = b"\xe0"


class FrenzMotorBridge:
    def __init__(self, args):
        self.args = args
        self.stop_requested = False
        self.serial_port = None
        self.last_cmd = 0
        self.last_eeg_ts = 0.0

        # EEG state
        self.fs = 125.0
        self.channel_idx = args.channel
        self.eeg_buffer = deque(maxlen=args.buffer_samples)
        self.atr_history = deque(maxlen=80)
        self.trend_history = deque(maxlen=120)
        self.trend_lp = 0.0
        self.cmd_lp = 0.0
        self.last_nonzero_sign = 1
        self.last_sign_change_ts = 0.0
        self.last_stats = None
        self.hist_cmd = deque(maxlen=80)
        self.hist_atr = deque(maxlen=80)
        self.hist_paf = deque(maxlen=80)
        self.hist_falloff = deque(maxlen=80)

        # CSV logging state
        self.csv_file = None
        self.csv_writer = None
        self.csv_path = args.csv_log
        self._init_csv()

    def _init_csv(self):
        if not self.csv_path:
            return
        try:
            already_exists = os.path.exists(self.csv_path)
            already_has_data = already_exists and os.path.getsize(self.csv_path) > 0
            self.csv_file = open(self.csv_path, "a", newline="", buffering=1)
            self.csv_writer = csv.writer(self.csv_file)
            if not already_has_data:
                self.csv_writer.writerow(
                    [
                        "unix_ts",
                        "iso_ts",
                        "status",
                        "eeg_age_s",
                        "cmd",
                        "atr",
                        "atr_trend",
                        "paf_hz",
                        "one_over_f_slope",
                        "one_over_f_falloff",
                        "alpha_power",
                        "theta_power",
                    ]
                )
            print(f"[CSV] logging enabled: {self.csv_path}")
        except Exception as exc:
            print(f"[CSV] logging disabled (open failed): {exc}")
            self.csv_file = None
            self.csv_writer = None
            self.csv_path = ""

    def _log_csv(self, status, cmd, eeg_age_s, stats):
        if not self.csv_writer:
            return
        now = time.time()
        iso = datetime.fromtimestamp(now, tz=timezone.utc).isoformat()
        if stats is None:
            atr = ""
            trend = ""
            paf = ""
            slope = ""
            falloff = ""
            alpha = ""
            theta = ""
        else:
            atr = stats["atr"]
            trend = stats["trend"]
            paf = stats["paf"]
            slope = stats["one_over_f_slope"]
            falloff = (-slope if not np.isnan(slope) else float("nan"))
            alpha = stats["alpha"]
            theta = stats["theta"]

        self.csv_writer.writerow(
            [
                f"{now:.3f}",
                iso,
                status,
                f"{eeg_age_s:.3f}",
                int(cmd),
                atr,
                trend,
                paf,
                slope,
                falloff,
                alpha,
                theta,
            ]
        )
        self.csv_file.flush()

    @staticmethod
    def _spark(values, vmin, vmax, width=56):
        if not values:
            return "." * width
        levels = " .:-=+*#%@"
        vals = list(values)
        if len(vals) < width:
            vals = [vals[0]] * (width - len(vals)) + vals
        else:
            vals = vals[-width:]
        span = (vmax - vmin) if (vmax - vmin) != 0 else 1.0
        out = []
        for v in vals:
            x = (v - vmin) / span
            x = 0.0 if x < 0 else 1.0 if x > 1 else x
            idx = int(round(x * (len(levels) - 1)))
            out.append(levels[idx])
        return "".join(out)

    def _render_dashboard(self, cmd, stats, eeg_age_s):
        if not self.args.dashboard:
            return
        if not sys.stdout.isatty():
            return
        if stats is None:
            return

        atr = stats["atr"]
        paf = stats["paf"]
        slope = stats["one_over_f_slope"]
        falloff = -slope if not np.isnan(slope) else float("nan")
        trend = stats["trend"]

        self.hist_cmd.append(float(cmd))
        self.hist_atr.append(float(atr))
        self.hist_paf.append(float(paf if not np.isnan(paf) else 0.0))
        self.hist_falloff.append(float(falloff if not np.isnan(falloff) else 0.0))

        cmd_bar = self._spark(self.hist_cmd, -50.0, 50.0)
        atr_bar = self._spark(self.hist_atr, 0.0, 10.0)
        paf_bar = self._spark(self.hist_paf, 8.0, 13.0)
        fall_bar = self._spark(self.hist_falloff, -0.5, 2.0)

        print("\033[2J\033[H", end="")
        print("FRENZ EEG -> MOTOR LIVE DASHBOARD")
        print(f"status=ok eeg_age={eeg_age_s:.2f}s cmd={cmd:+d} trend={trend:+.5f}")
        print(
            f"atr={atr:.3f}  paf={paf:.2f}Hz  1/f_slope={slope:+.3f}  "
            f"falloff={falloff:.3f}"
        )
        print(f"alpha={stats['alpha']:.1f}  theta={stats['theta']:.1f}")
        print("")
        print(f"CMD [-50..+50]   |{cmd_bar}|")
        print(f"ATR [0..10]      |{atr_bar}|")
        print(f"PAF [8..13 Hz]   |{paf_bar}|")
        print(f"1/f falloff      |{fall_bar}|")
        print("")
        print(f"csv={self.csv_path}")
        print("Ctrl+C to stop")
        sys.stdout.flush()

    def install_signal_handlers(self):
        def _handler(_sig, _frame):
            self.stop_requested = True
        signal.signal(signal.SIGINT, _handler)
        signal.signal(signal.SIGTERM, _handler)

    def _ensure_serial(self):
        if self.serial_port and self.serial_port.is_open:
            return True
        try:
            self.serial_port = serial.Serial(
                self.args.serial_port, self.args.baud, timeout=0, write_timeout=0
            )
            time.sleep(0.4)
            print(f"[SERIAL] connected {self.args.serial_port} @ {self.args.baud}")
            return True
        except Exception as exc:
            print(f"[SERIAL] connect failed: {exc}")
            self.serial_port = None
            return False

    def _send_cmd(self, cmd):
        if cmd == self.last_cmd and not self.args.resend_same:
            return
        if not self._ensure_serial():
            return
        try:
            self.serial_port.write(f"{int(cmd)}\n".encode())
            self.serial_port.flush()
            self.last_cmd = int(cmd)
        except Exception as exc:
            print(f"[SERIAL] write failed: {exc}")
            try:
                self.serial_port.close()
            except Exception:
                pass
            self.serial_port = None

    def _decode_eeg_packet(self, data):
        # Expect little-endian int16 stream.
        vals = np.frombuffer(data, dtype="<i2")
        if vals.size < 6:
            return None
        rem = vals.size % 6
        if rem:
            vals = vals[: vals.size - rem]
        if vals.size < 6:
            return None
        arr = vals.reshape(-1, 6)
        ch = min(max(self.channel_idx, 0), 5)
        return arr[:, ch].astype(np.float64)

    def _on_eeg(self, _sender, data):
        ch_samples = self._decode_eeg_packet(bytes(data))
        if ch_samples is None:
            return
        for s in ch_samples:
            self.eeg_buffer.append(s)
        self.last_eeg_ts = time.time()

    def _on_cmd_res(self, _sender, data):
        if self.args.verbose_ble:
            print(f"[BLE] cmd-res {bytes(data).hex()}")

    async def _send_ble_cmd(self, client, payload, label):
        try:
            await client.write_gatt_char(CMD_RX_UUID, payload, response=False)
            if self.args.verbose_ble:
                print(f"[BLE] sent {label}: {payload.hex()}")
            await asyncio.sleep(0.15)
        except Exception as exc:
            print(f"[BLE] send {label} failed: {exc}")

    def _compute_motor_cmd_from_buffer(self):
        if len(self.eeg_buffer) < 256:
            return 0, None

        y = np.array(self.eeg_buffer, dtype=np.float64)
        y = y - np.mean(y)
        f, pxx = spsig.welch(y, self.fs, nperseg=256)
        pxx_safe = np.maximum(pxx, 1e-12)

        theta = float(np.sum(pxx_safe[(f >= 4) & (f < 8)]))
        alpha = float(np.sum(pxx_safe[(f >= 8) & (f < 13)]))
        atr = alpha / (theta + 1.0)
        self.atr_history.append(atr)

        # Peak Alpha Frequency (PAF): argmax power in 8-13 Hz.
        paf = float("nan")
        alpha_mask = (f >= 8) & (f < 13)
        if np.any(alpha_mask):
            f_alpha = f[alpha_mask]
            p_alpha = pxx_safe[alpha_mask]
            paf = float(f_alpha[int(np.argmax(p_alpha))])

        # 1/f falloff as slope in log-log PSD from 2-30 Hz.
        # More negative slope => steeper falloff.
        one_over_f_slope = float("nan")
        fit_mask = (f >= 2) & (f <= 30)
        if np.count_nonzero(fit_mask) >= 8:
            x = np.log10(f[fit_mask])
            ylog = np.log10(pxx_safe[fit_mask])
            one_over_f_slope = float(np.polyfit(x, ylog, 1)[0])

        if len(self.atr_history) < 10:
            return 0, {
                "alpha": alpha,
                "theta": theta,
                "atr": atr,
                "trend": 0.0,
                "paf": paf,
                "one_over_f_slope": one_over_f_slope,
            }

        hist = np.array(self.atr_history, dtype=np.float64)
        current = float(np.mean(hist[-4:]))
        past = float(np.mean(hist[:-4]))
        trend = current - past
        self.trend_history.append(trend)

        # Smooth trend and command to avoid buzzy sign flapping.
        self.trend_lp = 0.72 * self.trend_lp + 0.28 * trend
        scale = np.percentile(np.abs(np.array(self.trend_history)), 85) + 1e-9
        norm = self.trend_lp / scale
        raw_cmd = float(np.clip(54.0 * math.tanh(1.2 * norm), -54, 54))
        self.cmd_lp = 0.70 * self.cmd_lp + 0.30 * raw_cmd
        mag = abs(self.cmd_lp)

        # Quantize to torque-friendlier bands for this stepper/driver combo.
        if mag < 9:
            qmag = 0
        elif mag < 14:
            qmag = 12
        elif mag < 22:
            qmag = 18
        elif mag < 30:
            qmag = 26
        elif mag < 40:
            qmag = 34
        elif mag < 48:
            qmag = 42
        else:
            qmag = 50

        now = time.time()
        proposed_sign = 1 if self.cmd_lp >= 0 else -1
        if qmag == 0:
            sign = self.last_nonzero_sign
        else:
            sign = proposed_sign
            # Prevent rapid reversals that cause vibration without rotation.
            if sign != self.last_nonzero_sign:
                can_flip = (
                    (now - self.last_sign_change_ts) >= 0.90 and qmag >= 26
                )
                if not can_flip:
                    sign = self.last_nonzero_sign
                else:
                    self.last_nonzero_sign = sign
                    self.last_sign_change_ts = now

        cmd = int(sign * qmag)

        return cmd, {
            "alpha": alpha,
            "theta": theta,
            "atr": atr,
            "trend": trend,
            "paf": paf,
            "one_over_f_slope": one_over_f_slope,
        }

    async def run(self):
        self.install_signal_handlers()

        while not self.stop_requested:
            print(f"[BLE] scanning for {self.args.device_name} ...")
            target = None
            try:
                devices = await asyncio.wait_for(
                    BleakScanner.discover(timeout=8.0, return_adv=True), timeout=12.0
                )
                for device, adv in devices.values():
                    name = device.name or adv.local_name or ""
                    if self.args.device_name.upper() in name.upper():
                        target = device
                        break
            except asyncio.TimeoutError:
                print("[BLE] scan timeout, retrying...")
                await asyncio.sleep(1.0)
                continue
            except Exception as exc:
                print(f"[BLE] scan error: {exc}")
                await asyncio.sleep(1.0)
                continue

            if not target:
                print("[BLE] device not found, retrying...")
                await asyncio.sleep(1.0)
                continue

            print(f"[BLE] connecting {target.name} ({target.address})")
            try:
                async with BleakClient(target.address, timeout=20.0) as client:
                    print("[BLE] connected")
                    self.last_eeg_ts = time.time()

                    await client.start_notify(CMD_RES_UUID, self._on_cmd_res)
                    await client.start_notify(EEG_STREAM_UUID, self._on_eeg)

                    await self._send_ble_cmd(client, CMD_ON_CONNECTED, "ON_CONNECTED")
                    await self._send_ble_cmd(client, CMD_START_NOTIFY_DATA, "START_NOTIFY_DATA")
                    await self._send_ble_cmd(
                        client, CMD_DATA_STREAM_CTRL + b"\x01", "DATA_STREAM_CTRL_START"
                    )

                    print("[RUN] live EEG motor bridge running")
                    while client.is_connected and not self.stop_requested:
                        now = time.time()
                        age = now - self.last_eeg_ts
                        if age > self.args.eeg_timeout_s:
                            if self.last_cmd != 0:
                                print(f"[TIMEOUT] EEG stale for {age:.2f}s -> motor stop")
                            self._send_cmd(0)
                            self._log_csv("timeout", 0, age, self.last_stats)
                            await asyncio.sleep(self.args.dt)
                            continue

                        cmd, stats = self._compute_motor_cmd_from_buffer()
                        self.last_stats = stats
                        self._send_cmd(cmd)

                        if stats is None:
                            self._log_csv("warmup", cmd, age, None)
                            print("[EEG] warming up buffer ...", end="\r", flush=True)
                        else:
                            alpha = stats["alpha"]
                            theta = stats["theta"]
                            atr = stats["atr"]
                            trend = stats["trend"]
                            paf = stats["paf"]
                            slope = stats["one_over_f_slope"]
                            falloff = -slope if not np.isnan(slope) else float("nan")
                            print(
                                f"[EEG] cmd={cmd:+4d} atr={atr:6.3f} trend={trend:+.5f} "
                                f"paf={paf:5.2f}Hz 1/f_slope={slope:+.3f} "
                                f"falloff={falloff:.3f} "
                                f"alpha={alpha:10.1f} theta={theta:10.1f}",
                                end="\r",
                                flush=True,
                            )
                            self._render_dashboard(cmd, stats, age)
                            self._log_csv("ok", cmd, age, stats)
                        await asyncio.sleep(self.args.dt)

                    # Graceful device-side stop.
                    try:
                        await self._send_ble_cmd(
                            client, CMD_DATA_STREAM_CTRL + b"\x00", "DATA_STREAM_CTRL_STOP"
                        )
                        await self._send_ble_cmd(client, CMD_OFF_CONNECTED, "OFF_CONNECTED")
                    except Exception:
                        pass
            except Exception as exc:
                print(f"\n[BLE] session error: {exc}")

            # On disconnect/failure, stop motor for safety.
            self._send_cmd(0)
            await asyncio.sleep(1.0)

        self._send_cmd(0)
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()
            except Exception:
                pass
        if self.csv_file:
            try:
                self.csv_file.close()
            except Exception:
                pass
        print("\n[RUN] stopped")


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--device-name", default=DEVICE_NAME_DEFAULT)
    p.add_argument("--serial-port", default="/dev/cu.usbmodemDC5475EAE5A42")
    p.add_argument("--baud", type=int, default=9600)
    p.add_argument("--channel", type=int, default=4, help="EEG channel index 0..5")
    p.add_argument("--buffer-samples", type=int, default=500)
    p.add_argument("--dt", type=float, default=0.10)
    p.add_argument("--eeg-timeout-s", type=float, default=2.5)
    p.add_argument(
        "--csv-log",
        default="/tmp/frenz_ble_motor_metrics.csv",
        help="CSV output path (set empty string to disable)",
    )
    p.add_argument("--dashboard", dest="dashboard", action="store_true", default=True)
    p.add_argument("--no-dashboard", dest="dashboard", action="store_false")
    p.add_argument("--resend-same", action="store_true")
    p.add_argument("--verbose-ble", action="store_true")
    return p.parse_args()


def main():
    args = parse_args()
    bridge = FrenzMotorBridge(args)
    asyncio.run(bridge.run())


if __name__ == "__main__":
    main()
