#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from scipy import stats


METRICS = [
    "paf_hz",
    "alpha_theta_ratio",
    "gamma_delta_ratio",
    "one_over_f_slope",
    "one_over_f_r2",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare the next 1-minute eyes-closed block against the previous archived minute."
    )
    parser.add_argument("--duration-sec", type=float, default=60.0)
    parser.add_argument("--baseline-sec", type=float, default=60.0)
    parser.add_argument("--poll-sec", type=float, default=0.5)
    parser.add_argument(
        "--payload-path",
        type=Path,
        default=Path("/Users/simfish/Documents/GitHub/gaia-hackathon-2026/openbci_live_payload.json"),
    )
    parser.add_argument(
        "--summary-path",
        type=Path,
        default=Path("/Users/simfish/Documents/GitHub/gaia-hackathon-2026/eyes_closed_compare_summary.txt"),
    )
    parser.add_argument(
        "--json-path",
        type=Path,
        default=Path("/Users/simfish/Documents/GitHub/gaia-hackathon-2026/eyes_closed_compare_summary.json"),
    )
    parser.add_argument("--d1-name", default="openbci-archive")
    parser.add_argument(
        "--wrangler-dir",
        type=Path,
        default=Path("/Users/simfish/Documents/GitHub/gaia-hackathon-2026/openbci_status_worker"),
    )
    parser.add_argument("--sound", default="Glass")
    return parser.parse_args()


def naive_iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def load_payload(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def query_d1(wrangler_dir: Path, database_name: str, command: str) -> list[dict]:
    proc = subprocess.run(
        [
            "npx",
            "wrangler",
            "d1",
            "execute",
            database_name,
            "--remote",
            f"--command={command}",
            "--json",
        ],
        cwd=str(wrangler_dir),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "wrangler d1 failed")
    payload = json.loads(proc.stdout)
    if not payload:
        return []
    return payload[0].get("results", [])


def recent_archived_rows(args: argparse.Namespace, start: datetime) -> list[dict]:
    baseline_start = naive_iso(start - timedelta(seconds=args.baseline_sec))
    baseline_end = naive_iso(start)
    sql = (
        "SELECT updated_at, paf_hz, alpha_theta_ratio, gamma_delta_ratio, one_over_f_slope, "
        "one_over_f_r2, artifact_flag, quality FROM eeg_snapshots "
        f"WHERE updated_at >= '{baseline_start}' AND updated_at < '{baseline_end}' "
        "ORDER BY updated_at ASC"
    )
    return query_d1(args.wrangler_dir, args.d1_name, sql)


def capture_segment(args: argparse.Namespace, start_monotonic: float, duration_sec: float) -> list[dict]:
    captured = []
    seen_updated_at: set[str] = set()
    while (time.monotonic() - start_monotonic) < duration_sec:
        payload = load_payload(args.payload_path)
        if payload:
            metrics = payload.get("metrics") or {}
            updated_at = str(payload.get("updated_at") or "")
            if updated_at and updated_at not in seen_updated_at:
                seen_updated_at.add(updated_at)
                captured.append(
                    {
                        "updated_at": updated_at,
                        "paf_hz": metrics.get("paf_hz"),
                        "alpha_theta_ratio": metrics.get("alpha_theta_ratio"),
                        "gamma_delta_ratio": metrics.get("gamma_delta_ratio"),
                        "one_over_f_slope": metrics.get("one_over_f_slope"),
                        "one_over_f_r2": metrics.get("one_over_f_r2"),
                        "artifact_flag": int(bool(metrics.get("artifact_flag"))),
                        "quality": metrics.get("quality"),
                    }
                )
        time.sleep(args.poll_sec)
    return captured


def finite_values(rows: list[dict], key: str) -> np.ndarray:
    values = []
    for row in rows:
        value = row.get(key)
        if value is None:
            continue
        try:
            value = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(value):
            values.append(value)
    return np.asarray(values, dtype=float)


def summarise_metric(baseline: list[dict], closed: list[dict], key: str) -> dict:
    base = finite_values(baseline, key)
    eyes = finite_values(closed, key)
    result = {
        "metric": key,
        "baseline_n": int(base.size),
        "closed_n": int(eyes.size),
        "baseline_median": None,
        "closed_median": None,
        "delta_median": None,
        "baseline_mean": None,
        "closed_mean": None,
        "p_value": None,
        "significant": False,
    }
    if base.size == 0 or eyes.size == 0:
        return result
    result["baseline_median"] = float(np.median(base))
    result["closed_median"] = float(np.median(eyes))
    result["delta_median"] = float(np.median(eyes) - np.median(base))
    result["baseline_mean"] = float(np.mean(base))
    result["closed_mean"] = float(np.mean(eyes))
    if base.size >= 3 and eyes.size >= 3:
        try:
            _, p_value = stats.mannwhitneyu(base, eyes, alternative="two-sided")
            result["p_value"] = float(p_value)
            result["significant"] = bool(p_value < 0.05)
        except Exception:
            pass
    return result


def quality_counts(rows: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        label = str(row.get("quality") or "unknown")
        counts[label] = counts.get(label, 0) + 1
    return counts


def artifact_rate(rows: list[dict]) -> float | None:
    if not rows:
        return None
    vals = [int(bool(row.get("artifact_flag"))) for row in rows]
    return float(np.mean(vals))


def format_value(value: float | None, digits: int = 3) -> str:
    if value is None or not math.isfinite(value):
        return "n/a"
    return f"{value:.{digits}f}"


def build_report(
    start: datetime,
    end: datetime,
    baseline: list[dict],
    closed: list[dict],
    metric_summaries: list[dict],
) -> str:
    lines = [
        "Eyes-Closed Comparison",
        f"baseline_window: {naive_iso(start - timedelta(seconds=60))} to {naive_iso(start)}",
        f"closed_window: {naive_iso(start)} to {naive_iso(end)}",
        f"baseline_snapshots: {len(baseline)}",
        f"closed_snapshots: {len(closed)}",
        f"baseline_artifact_rate: {format_value(artifact_rate(baseline), 2)}",
        f"closed_artifact_rate: {format_value(artifact_rate(closed), 2)}",
        f"baseline_quality_counts: {json.dumps(quality_counts(baseline), sort_keys=True)}",
        f"closed_quality_counts: {json.dumps(quality_counts(closed), sort_keys=True)}",
        "",
    ]
    for item in metric_summaries:
        lines.extend(
            [
                f"[{item['metric']}]",
                f"baseline_median: {format_value(item['baseline_median'])}",
                f"closed_median: {format_value(item['closed_median'])}",
                f"delta_median: {format_value(item['delta_median'])}",
                f"baseline_mean: {format_value(item['baseline_mean'])}",
                f"closed_mean: {format_value(item['closed_mean'])}",
                f"p_value: {format_value(item['p_value'])}",
                f"significant: {str(item['significant']).lower()}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def play_sound(name: str) -> None:
    sound_path = f"/System/Library/Sounds/{name}.aiff"
    proc = subprocess.run(["afplay", sound_path], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        subprocess.run(["osascript", "-e", "beep 3"], check=False)


def main() -> int:
    args = parse_args()
    started_dt = datetime.now()
    baseline = recent_archived_rows(args, started_dt)
    started_monotonic = time.monotonic()
    closed = capture_segment(args, started_monotonic, args.duration_sec)
    ended_dt = datetime.now()
    play_sound(args.sound)

    metric_summaries = [summarise_metric(baseline, closed, key) for key in METRICS]
    report = build_report(started_dt, ended_dt, baseline, closed, metric_summaries)
    summary = {
        "started_at": naive_iso(started_dt),
        "ended_at": naive_iso(ended_dt),
        "baseline_snapshots": baseline,
        "closed_snapshots": closed,
        "metrics": metric_summaries,
        "baseline_artifact_rate": artifact_rate(baseline),
        "closed_artifact_rate": artifact_rate(closed),
        "baseline_quality_counts": quality_counts(baseline),
        "closed_quality_counts": quality_counts(closed),
    }
    args.summary_path.write_text(report)
    args.json_path.write_text(json.dumps(summary, indent=2))
    print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
