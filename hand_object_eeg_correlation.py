#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy import stats


@dataclass
class JointSample:
    timestamp: str
    unix_time: float
    held_object_candidate: bool
    hand_candidate_count: int
    unusual_motion: bool
    activity_level: str
    gamma_power: float
    delta_power: float
    gamma_delta_ratio: float
    alpha_theta_ratio: float
    one_over_f_slope: float
    one_over_f_r2: float
    beta_power: float
    hf_power: float
    hf_spike: bool


METRICS = [
    "gamma_power",
    "hf_power",
    "gamma_delta_ratio",
    "beta_power",
    "alpha_theta_ratio",
    "one_over_f_slope",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Correlate held-object webcam tags with high-frequency EEG activity.")
    parser.add_argument("--duration-sec", type=float, default=90.0)
    parser.add_argument("--interval-sec", type=float, default=0.25)
    parser.add_argument(
        "--webcam-json-path",
        type=Path,
        default=Path("/Users/simfish/Documents/GitHub/gaia-hackathon-2026/webcam_event_status.json"),
    )
    parser.add_argument(
        "--eeg-payload-path",
        type=Path,
        default=Path("/Users/simfish/Documents/GitHub/gaia-hackathon-2026/openbci_live_payload.json"),
    )
    parser.add_argument(
        "--samples-path",
        type=Path,
        default=Path("/Users/simfish/Documents/GitHub/gaia-hackathon-2026/hand_object_eeg_samples.jsonl"),
    )
    parser.add_argument(
        "--summary-path",
        type=Path,
        default=Path("/Users/simfish/Documents/GitHub/gaia-hackathon-2026/hand_object_eeg_summary.txt"),
    )
    parser.add_argument(
        "--json-summary-path",
        type=Path,
        default=Path("/Users/simfish/Documents/GitHub/gaia-hackathon-2026/hand_object_eeg_summary.json"),
    )
    return parser.parse_args()


def load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def bandpower(freqs: np.ndarray, psd: np.ndarray, low: float, high: float) -> float:
    mask = (freqs >= low) & (freqs <= high)
    if not np.any(mask):
        return float("nan")
    return float(np.trapz(psd[mask], freqs[mask]))


def finite_array(rows: list[JointSample], attr: str) -> np.ndarray:
    values = []
    for row in rows:
        value = getattr(row, attr)
        if value is None:
            continue
        try:
            value = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(value):
            values.append(value)
    return np.asarray(values, dtype=float)


def summarize_metric(held_rows: list[JointSample], free_rows: list[JointSample], attr: str) -> dict[str, object]:
    held = finite_array(held_rows, attr)
    free = finite_array(free_rows, attr)
    result: dict[str, object] = {
        "metric": attr,
        "held_n": int(held.size),
        "free_n": int(free.size),
        "held_median": None,
        "free_median": None,
        "delta_median": None,
        "held_mean": None,
        "free_mean": None,
        "p_value": None,
        "significant": False,
    }
    if held.size == 0 or free.size == 0:
        return result
    result["held_median"] = float(np.median(held))
    result["free_median"] = float(np.median(free))
    result["delta_median"] = float(np.median(held) - np.median(free))
    result["held_mean"] = float(np.mean(held))
    result["free_mean"] = float(np.mean(free))
    if held.size >= 3 and free.size >= 3:
        try:
            _, p = stats.mannwhitneyu(held, free, alternative="two-sided")
            result["p_value"] = float(p)
            result["significant"] = bool(p < 0.05)
        except Exception:
            pass
    return result


def fmt(value: object, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(value):
        return "n/a"
    return f"{value:.{digits}f}"


def main() -> int:
    args = parse_args()
    started = time.monotonic()
    seen_pairs: set[tuple[str, str]] = set()
    records: list[JointSample] = []
    args.samples_path.write_text("")

    while (time.monotonic() - started) < args.duration_sec:
        webcam = load_json(args.webcam_json_path)
        eeg = load_json(args.eeg_payload_path)
        if webcam and eeg:
            webcam_ts = str(webcam.get("timestamp") or "")
            eeg_ts = str(eeg.get("updated_at") or "")
            pair = (webcam_ts, eeg_ts)
            if webcam_ts and eeg_ts and pair not in seen_pairs:
                seen_pairs.add(pair)
                metrics = eeg.get("metrics") or {}
                spectrum = eeg.get("spectrum") or {}
                freqs = np.asarray(spectrum.get("frequencies_hz") or [], dtype=float)
                median_psd = np.asarray(spectrum.get("median_psd") or [], dtype=float)
                beta_power = bandpower(freqs, median_psd, 13.0, 30.0) if freqs.size and median_psd.size else float("nan")
                hf_power = bandpower(freqs, median_psd, 30.0, 45.0) if freqs.size and median_psd.size else float("nan")
                sample = JointSample(
                    timestamp=eeg_ts,
                    unix_time=float(metrics.get("unix_time") or time.time()),
                    held_object_candidate=bool(webcam.get("held_object_candidate")),
                    hand_candidate_count=int(webcam.get("hand_candidate_count") or 0),
                    unusual_motion=bool(webcam.get("unusual_motion")),
                    activity_level=str(webcam.get("activity_level") or "unknown"),
                    gamma_power=float(metrics.get("gamma_power") or float("nan")),
                    delta_power=float(metrics.get("delta_power") or float("nan")),
                    gamma_delta_ratio=float(metrics.get("gamma_delta_ratio") or float("nan")),
                    alpha_theta_ratio=float(metrics.get("alpha_theta_ratio") or float("nan")),
                    one_over_f_slope=float(metrics.get("one_over_f_slope") or float("nan")),
                    one_over_f_r2=float(metrics.get("one_over_f_r2") or float("nan")),
                    beta_power=beta_power,
                    hf_power=hf_power,
                    hf_spike=False,
                )
                records.append(sample)
                with args.samples_path.open("a") as handle:
                    handle.write(json.dumps(sample.__dict__) + "\n")
        time.sleep(args.interval_sec)

    if not records:
        args.summary_path.write_text("No joint samples were captured.\n")
        args.json_summary_path.write_text(json.dumps({"error": "no_joint_samples"}, indent=2))
        print("No joint samples were captured.")
        return 1

    free_rows = [row for row in records if not row.held_object_candidate]
    held_rows = [row for row in records if row.held_object_candidate]

    free_gamma_ratio = finite_array(free_rows, "gamma_delta_ratio")
    free_hf = finite_array(free_rows, "hf_power")
    if free_gamma_ratio.size >= 5:
        gamma_threshold = float(np.median(free_gamma_ratio) + 2.0 * stats.median_abs_deviation(free_gamma_ratio, scale="normal"))
    else:
        gamma_threshold = float(np.nanpercentile(finite_array(records, "gamma_delta_ratio"), 90))
    if free_hf.size >= 5:
        hf_threshold = float(np.median(free_hf) + 2.0 * stats.median_abs_deviation(free_hf, scale="normal"))
    else:
        hf_threshold = float(np.nanpercentile(finite_array(records, "hf_power"), 90))

    for row in records:
        row.hf_spike = bool(
            (math.isfinite(row.gamma_delta_ratio) and row.gamma_delta_ratio >= gamma_threshold)
            or (math.isfinite(row.hf_power) and row.hf_power >= hf_threshold)
        )

    free_rows = [row for row in records if not row.held_object_candidate]
    held_rows = [row for row in records if row.held_object_candidate]
    metric_summaries = [summarize_metric(held_rows, free_rows, attr) for attr in METRICS]

    held_spike_rate = statistics.mean([row.hf_spike for row in held_rows]) if held_rows else None
    free_spike_rate = statistics.mean([row.hf_spike for row in free_rows]) if free_rows else None
    unusual_when_held = statistics.mean([row.unusual_motion for row in held_rows]) if held_rows else None

    report_lines = [
        "Held-Object vs EEG High-Frequency Comparison",
        f"duration_seconds: {fmt(args.duration_sec, 1)}",
        f"joint_samples: {len(records)}",
        f"held_samples: {len(held_rows)}",
        f"free_samples: {len(free_rows)}",
        f"gamma_ratio_spike_threshold: {fmt(gamma_threshold)}",
        f"hf_power_spike_threshold: {fmt(hf_threshold)}",
        f"held_spike_rate: {fmt(held_spike_rate, 3)}",
        f"free_spike_rate: {fmt(free_spike_rate, 3)}",
        f"held_unusual_motion_rate: {fmt(unusual_when_held, 3)}",
        "",
    ]
    for item in metric_summaries:
        report_lines.extend(
            [
                f"[{item['metric']}]",
                f"held_median: {fmt(item['held_median'])}",
                f"free_median: {fmt(item['free_median'])}",
                f"delta_median: {fmt(item['delta_median'])}",
                f"held_mean: {fmt(item['held_mean'])}",
                f"free_mean: {fmt(item['free_mean'])}",
                f"p_value: {fmt(item['p_value'])}",
                f"significant: {str(item['significant']).lower()}",
                "",
            ]
        )

    report = "\n".join(report_lines).rstrip() + "\n"
    args.summary_path.write_text(report)
    args.json_summary_path.write_text(
        json.dumps(
            {
                "samples": len(records),
                "held_samples": len(held_rows),
                "free_samples": len(free_rows),
                "gamma_ratio_spike_threshold": gamma_threshold,
                "hf_power_spike_threshold": hf_threshold,
                "held_spike_rate": held_spike_rate,
                "free_spike_rate": free_spike_rate,
                "held_unusual_motion_rate": unusual_when_held,
                "metrics": metric_summaries,
            },
            indent=2,
        )
    )
    print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
