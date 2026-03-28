#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path

import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute fixation-style metrics from webcam eye-tracker logs.")
    parser.add_argument(
        "--log-path",
        type=Path,
        default=Path("/Users/simfish/Documents/GitHub/gaia-hackathon-2026/webcam_eye_log.jsonl"),
    )
    parser.add_argument(
        "--summary-path",
        type=Path,
        default=Path("/Users/simfish/Documents/GitHub/gaia-hackathon-2026/webcam_eye_fixation_summary.txt"),
    )
    parser.add_argument(
        "--json-summary-path",
        type=Path,
        default=Path("/Users/simfish/Documents/GitHub/gaia-hackathon-2026/webcam_eye_fixation_summary.json"),
    )
    parser.add_argument("--saccade-threshold", type=float, default=0.12, help="Normalized gaze-step threshold.")
    parser.add_argument("--fixation-threshold", type=float, default=0.04, help="Normalized gaze-step threshold for fixation continuity.")
    return parser.parse_args()


def load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def fmt(value: float | None, digits: int = 3) -> str:
    if value is None or not math.isfinite(value):
        return "n/a"
    return f"{value:.{digits}f}"


def episode_durations(flags: list[bool], times: np.ndarray) -> list[float]:
    durations: list[float] = []
    if not flags:
        return durations
    start_idx = None
    for idx, flag in enumerate(flags):
        if flag and start_idx is None:
            start_idx = idx
        elif not flag and start_idx is not None:
            durations.append(float(times[idx - 1] - times[start_idx]))
            start_idx = None
    if start_idx is not None:
        durations.append(float(times[-1] - times[start_idx]))
    return durations


def fixation_episode_lengths(steps: np.ndarray, times: np.ndarray, threshold: float) -> list[float]:
    if steps.size == 0:
        return []
    durations: list[float] = []
    start_idx = 0
    for idx, step in enumerate(steps, start=1):
        if not math.isfinite(step) or step > threshold:
            if idx - 1 > start_idx:
                durations.append(float(times[idx - 1] - times[start_idx]))
            start_idx = idx
    if len(times) - 1 > start_idx:
        durations.append(float(times[-1] - times[start_idx]))
    return durations


def main() -> int:
    args = parse_args()
    rows = load_rows(args.log_path)
    valid = [r for r in rows if r.get("gaze_x") is not None and r.get("gaze_y") is not None and float(r.get("confidence", 0)) > 0]
    if not valid:
        report = "No valid gaze samples found.\n"
        args.summary_path.write_text(report)
        args.json_summary_path.write_text(json.dumps({"error": "no_valid_samples"}, indent=2))
        print(report, end="")
        return 1

    times = np.asarray([float(r["unix_time"]) for r in valid], dtype=float)
    xs = np.asarray([float(r["gaze_x"]) for r in valid], dtype=float)
    ys = np.asarray([float(r["gaze_y"]) for r in valid], dtype=float)
    confs = np.asarray([float(r["confidence"]) for r in valid], dtype=float)
    hz = [str(r["gaze_horizontal"]) for r in valid]
    vt = [str(r["gaze_vertical"]) for r in valid]

    duration = float(times[-1] - times[0]) if len(times) > 1 else 0.0
    deltas = np.sqrt(np.diff(xs) ** 2 + np.diff(ys) ** 2)
    saccade_count = int(np.sum(deltas > args.saccade_threshold))
    saccade_rate_hz = float(saccade_count / duration) if duration > 0 else float("nan")

    center_flags = [(h == "center" and v == "center") for h, v in zip(hz, vt)]
    peripheral_flags = [not flag for flag in center_flags]
    center_episodes = episode_durations(center_flags, times)
    peripheral_episodes = episode_durations(peripheral_flags, times)
    fixation_episodes = fixation_episode_lengths(deltas, times, args.fixation_threshold)

    summary = {
        "samples_total": len(rows),
        "samples_valid": len(valid),
        "duration_seconds": duration,
        "mean_gaze_x": float(np.mean(xs)),
        "mean_gaze_y": float(np.mean(ys)),
        "std_gaze_x": float(np.std(xs)),
        "std_gaze_y": float(np.std(ys)),
        "range_gaze_x": float(np.max(xs) - np.min(xs)),
        "range_gaze_y": float(np.max(ys) - np.min(ys)),
        "mean_confidence": float(np.mean(confs)),
        "horizontal_counts": dict(Counter(hz)),
        "vertical_counts": dict(Counter(vt)),
        "center_occupancy_fraction": float(np.mean(center_flags)),
        "peripheral_occupancy_fraction": float(np.mean(peripheral_flags)),
        "center_dwell_mean_seconds": float(np.mean(center_episodes)) if center_episodes else None,
        "center_dwell_max_seconds": float(np.max(center_episodes)) if center_episodes else None,
        "peripheral_dwell_mean_seconds": float(np.mean(peripheral_episodes)) if peripheral_episodes else None,
        "peripheral_dwell_max_seconds": float(np.max(peripheral_episodes)) if peripheral_episodes else None,
        "fixation_episode_count": len(fixation_episodes),
        "fixation_episode_mean_seconds": float(np.mean(fixation_episodes)) if fixation_episodes else None,
        "fixation_episode_max_seconds": float(np.max(fixation_episodes)) if fixation_episodes else None,
        "saccade_count": saccade_count,
        "saccade_rate_hz": saccade_rate_hz,
    }

    report = "\n".join(
        [
            "Eye Fixation Metrics",
            f"log_path: {args.log_path}",
            f"samples_total: {summary['samples_total']}",
            f"samples_valid: {summary['samples_valid']}",
            f"duration_seconds: {fmt(summary['duration_seconds'], 2)}",
            f"mean_gaze_x: {fmt(summary['mean_gaze_x'])}",
            f"mean_gaze_y: {fmt(summary['mean_gaze_y'])}",
            f"std_gaze_x: {fmt(summary['std_gaze_x'])}",
            f"std_gaze_y: {fmt(summary['std_gaze_y'])}",
            f"range_gaze_x: {fmt(summary['range_gaze_x'])}",
            f"range_gaze_y: {fmt(summary['range_gaze_y'])}",
            f"mean_confidence: {fmt(summary['mean_confidence'])}",
            f"horizontal_counts: {json.dumps(summary['horizontal_counts'], sort_keys=True)}",
            f"vertical_counts: {json.dumps(summary['vertical_counts'], sort_keys=True)}",
            f"center_occupancy_fraction: {fmt(summary['center_occupancy_fraction'])}",
            f"peripheral_occupancy_fraction: {fmt(summary['peripheral_occupancy_fraction'])}",
            f"center_dwell_mean_seconds: {fmt(summary['center_dwell_mean_seconds'], 2)}",
            f"center_dwell_max_seconds: {fmt(summary['center_dwell_max_seconds'], 2)}",
            f"peripheral_dwell_mean_seconds: {fmt(summary['peripheral_dwell_mean_seconds'], 2)}",
            f"peripheral_dwell_max_seconds: {fmt(summary['peripheral_dwell_max_seconds'], 2)}",
            f"fixation_episode_count: {summary['fixation_episode_count']}",
            f"fixation_episode_mean_seconds: {fmt(summary['fixation_episode_mean_seconds'], 2)}",
            f"fixation_episode_max_seconds: {fmt(summary['fixation_episode_max_seconds'], 2)}",
            f"saccade_count: {summary['saccade_count']}",
            f"saccade_rate_hz: {fmt(summary['saccade_rate_hz'], 3)}",
            "",
        ]
    )

    args.summary_path.write_text(report)
    args.json_summary_path.write_text(json.dumps(summary, indent=2))
    print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
