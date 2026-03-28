#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import time
from collections import Counter
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


SPOTIFY_DELIM = " ||| "
METRIC_KEYS = [
    "paf_hz",
    "alpha_theta_ratio",
    "gamma_delta_ratio",
    "one_over_f_slope",
    "one_over_f_r2",
]
METRIC_LABELS = {
    "paf_hz": "PAF (Hz)",
    "alpha_theta_ratio": "Alpha/Theta",
    "gamma_delta_ratio": "Gamma/Delta",
    "one_over_f_slope": "1/f slope",
    "one_over_f_r2": "1/f r²",
}


@dataclass
class SpotifyState:
    timestamp: str
    unix_time: float
    running: bool
    player_state: str
    artist: str | None
    track: str | None
    album: str | None
    uri: str | None
    duration_ms: int | None
    position_sec: float | None
    inferred_frequency_hz: float | None


@dataclass
class EegState:
    timestamp: str
    unix_time: float
    updated_at: str | None
    paf_hz: float | None
    alpha_theta_ratio: float | None
    gamma_delta_ratio: float | None
    one_over_f_slope: float | None
    one_over_f_r2: float | None
    quality: str | None
    artifact_flag: bool
    eye_state: str | None


@dataclass
class EventResult:
    event_index: int
    changed_at: str
    baseline_start: str
    baseline_end: str
    response_start: str
    response_end: str
    from_track: str | None
    to_track: str | None
    from_artist: str | None
    to_artist: str | None
    from_uri: str | None
    to_uri: str | None
    from_frequency_hz: float | None
    to_frequency_hz: float | None
    baseline_count: int
    response_count: int
    baseline_eye_state: str | None
    response_eye_state: str | None
    baseline_metrics: dict[str, float | None]
    response_metrics: dict[str, float | None]
    delta_metrics: dict[str, float | None]
    screenshot_path: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Watch Spotify track changes and compare pre/post EEG averages."
    )
    parser.add_argument("--poll-sec", type=float, default=1.0)
    parser.add_argument("--baseline-sec", type=float, default=30.0)
    parser.add_argument("--response-sec", type=float, default=30.0)
    parser.add_argument("--session-sec", type=float, default=180.0)
    parser.add_argument("--max-events", type=int, default=3)
    parser.add_argument(
        "--quality-alert-sec",
        type=float,
        default=20.0,
        help="Play a sound if EEG quality stays degraded for at least this long.",
    )
    parser.add_argument(
        "--quality-alert-cooldown-sec",
        type=float,
        default=45.0,
        help="Minimum time between repeated quality alerts while signal remains degraded.",
    )
    parser.add_argument("--quality-alert-sound", default="Basso")
    parser.add_argument(
        "--payload-path",
        type=Path,
        default=Path("/Users/simfish/Documents/GitHub/gaia-hackathon-2026/openbci_live_payload.json"),
    )
    parser.add_argument(
        "--eye-status-path",
        type=Path,
        default=Path("/Users/simfish/Documents/GitHub/gaia-hackathon-2026/webcam_eye_status.json"),
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("/Users/simfish/Documents/GitHub/gaia-hackathon-2026/spotify_eeg_change_results"),
    )
    parser.add_argument(
        "--summary-path",
        type=Path,
        default=Path("/Users/simfish/Documents/GitHub/gaia-hackathon-2026/spotify_eeg_change_summary.txt"),
    )
    parser.add_argument(
        "--json-path",
        type=Path,
        default=Path("/Users/simfish/Documents/GitHub/gaia-hackathon-2026/spotify_eeg_change_summary.json"),
    )
    return parser.parse_args()


def now_stamp() -> tuple[str, float]:
    unix_time = time.time()
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(unix_time)), unix_time


def infer_frequency_hz(*values: str | None) -> float | None:
    pattern = re.compile(r"(\d+(?:\.\d+)?)\s*hz", re.IGNORECASE)
    for value in values:
        if not value:
            continue
        match = pattern.search(value)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue
    return None


def slugify(value: str | None, fallback: str = "unknown-track") -> str:
    if not value:
        return fallback
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return cleaned[:80] or fallback


def timestamp_slug(value: str) -> str:
    return re.sub(r"[^0-9]+", "", value) or "unknown-time"


def query_spotify() -> SpotifyState:
    wall_time, unix_time = now_stamp()
    proc = subprocess.run(
        [
            "osascript",
            "-e",
            'if application "Spotify" is running then',
            "-e",
            f'tell application "Spotify" to return artist of current track & "{SPOTIFY_DELIM}" & name of current track & "{SPOTIFY_DELIM}" & album of current track & "{SPOTIFY_DELIM}" & id of current track & "{SPOTIFY_DELIM}" & (duration of current track as text) & "{SPOTIFY_DELIM}" & (player position as text) & "{SPOTIFY_DELIM}" & (player state as text)',
            "-e",
            "else",
            "-e",
            'return "NOT_RUNNING"',
            "-e",
            "end if",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    raw = (proc.stdout or "").strip()
    if proc.returncode != 0 or raw == "NOT_RUNNING" or not raw:
        return SpotifyState(
            timestamp=wall_time,
            unix_time=unix_time,
            running=False,
            player_state="stopped",
            artist=None,
            track=None,
            album=None,
            uri=None,
            duration_ms=None,
            position_sec=None,
            inferred_frequency_hz=None,
        )
    parts = raw.split(SPOTIFY_DELIM)
    if len(parts) != 7:
        return SpotifyState(
            timestamp=wall_time,
            unix_time=unix_time,
            running=True,
            player_state="unknown",
            artist=None,
            track=None,
            album=None,
            uri=None,
            duration_ms=None,
            position_sec=None,
            inferred_frequency_hz=None,
        )
    artist, track, album, uri, duration_text, position_text, player_state = [part.strip() for part in parts]
    try:
        duration_ms = int(float(duration_text))
    except ValueError:
        duration_ms = None
    try:
        position_sec = float(position_text)
    except ValueError:
        position_sec = None
    return SpotifyState(
        timestamp=wall_time,
        unix_time=unix_time,
        running=True,
        player_state=player_state,
        artist=artist or None,
        track=track or None,
        album=album or None,
        uri=uri or None,
        duration_ms=duration_ms,
        position_sec=position_sec,
        inferred_frequency_hz=infer_frequency_hz(track, album, artist),
    )


def load_eeg_state(payload_path: Path) -> EegState | None:
    try:
        payload = json.loads(payload_path.read_text())
    except Exception:
        return None
    metrics = payload.get("metrics") or {}
    wall_time, unix_time = now_stamp()
    return EegState(
        timestamp=wall_time,
        unix_time=unix_time,
        updated_at=payload.get("updated_at"),
        paf_hz=_finite(metrics.get("paf_hz")),
        alpha_theta_ratio=_finite(metrics.get("alpha_theta_ratio")),
        gamma_delta_ratio=_finite(metrics.get("gamma_delta_ratio")),
        one_over_f_slope=_finite(metrics.get("one_over_f_slope")),
        one_over_f_r2=_finite(metrics.get("one_over_f_r2")),
        quality=metrics.get("quality"),
        artifact_flag=bool(metrics.get("artifact_flag")),
        eye_state=None,
    )


def load_eye_state(path: Path) -> str | None:
    try:
        payload = json.loads(path.read_text())
    except Exception:
        return None
    value = payload.get("eye_state")
    return str(value) if value is not None else None


def _finite(value: object) -> float | None:
    try:
        value = float(value)
    except Exception:
        return None
    return value if math.isfinite(value) else None


def summarise_states(states: list[EegState]) -> dict[str, float | None]:
    summary: dict[str, float | None] = {}
    for key in METRIC_KEYS:
        vals = [getattr(state, key) for state in states]
        vals = [float(v) for v in vals if v is not None and math.isfinite(v)]
        summary[key] = float(np.mean(vals)) if vals else None
    artifact_vals = [1.0 if state.artifact_flag else 0.0 for state in states]
    summary["artifact_rate"] = float(np.mean(artifact_vals)) if artifact_vals else None
    return summary


def dominant_eye_state(states: list[EegState]) -> str | None:
    labels = [state.eye_state for state in states if state.eye_state]
    if not labels:
        return None
    counts = Counter(labels)
    return counts.most_common(1)[0][0]


def delta_metrics(response: dict[str, float | None], baseline: dict[str, float | None]) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for key in list(METRIC_KEYS) + ["artifact_rate"]:
        a = baseline.get(key)
        b = response.get(key)
        out[key] = None if a is None or b is None else float(b - a)
    return out


def fmt(value: float | None, digits: int = 3) -> str:
    if value is None or not math.isfinite(value):
        return "n/a"
    return f"{value:.{digits}f}"


def eeg_quality_is_degraded(state: EegState) -> bool:
    if state.artifact_flag:
        return True
    quality = (state.quality or "").strip().lower()
    return quality not in {"good", "excellent"}


def play_sound(name: str) -> None:
    sound_path = f"/System/Library/Sounds/{name}.aiff"
    proc = subprocess.run(["afplay", sound_path], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        subprocess.run(["osascript", "-e", "beep 2"], check=False)


def make_screenshot(
    event: EventResult,
    baseline_samples: list[EegState],
    response_samples: list[EegState],
) -> None:
    fig = plt.figure(figsize=(14, 8), dpi=140, constrained_layout=True)
    gs = fig.add_gridspec(2, 2, width_ratios=[1.0, 1.0], height_ratios=[1.0, 1.0])
    ax_base = fig.add_subplot(gs[0, 0])
    ax_resp = fig.add_subplot(gs[0, 1])
    ax_delta = fig.add_subplot(gs[1, 0])
    ax_text = fig.add_subplot(gs[1, 1])
    labels = [METRIC_LABELS[key] for key in METRIC_KEYS]
    base_vals = [event.baseline_metrics.get(key) for key in METRIC_KEYS]
    resp_vals = [event.response_metrics.get(key) for key in METRIC_KEYS]
    delta_vals = [event.delta_metrics.get(key) for key in METRIC_KEYS]
    y = np.arange(len(labels))

    ax_base.barh(y, [0 if v is None else v for v in base_vals], color="#74c0fc")
    ax_base.set_yticks(y)
    ax_base.set_yticklabels(labels)
    ax_base.invert_yaxis()
    ax_base.set_title("Baseline average")
    ax_base.grid(axis="x", alpha=0.2)

    ax_resp.barh(y, [0 if v is None else v for v in resp_vals], color="#ff922b")
    ax_resp.set_yticks(y)
    ax_resp.set_yticklabels(labels)
    ax_resp.invert_yaxis()
    ax_resp.set_title("Post-change average")
    ax_resp.grid(axis="x", alpha=0.2)

    delta_colors = ["#2b8a3e" if (v or 0) >= 0 else "#c92a2a" for v in delta_vals]
    ax_delta.barh(y, [0 if v is None else v for v in delta_vals], color=delta_colors)
    ax_delta.set_yticks(y)
    ax_delta.set_yticklabels(labels)
    ax_delta.invert_yaxis()
    ax_delta.axvline(0.0, color="#495057", linewidth=1)
    ax_delta.set_title("Delta (post - baseline)")
    ax_delta.grid(axis="x", alpha=0.2)

    ax_text.axis("off")
    lines = [
        f"Event {event.event_index}",
        f"Changed: {event.changed_at}",
        "",
        f"From: {event.from_artist or 'n/a'} - {event.from_track or 'n/a'}",
        f"To:   {event.to_artist or 'n/a'} - {event.to_track or 'n/a'}",
        f"Freq: {fmt(event.from_frequency_hz, 1)} Hz -> {fmt(event.to_frequency_hz, 1)} Hz",
        f"Eyes: {event.baseline_eye_state or 'unknown'} -> {event.response_eye_state or 'unknown'}",
        "",
        f"Baseline samples: {event.baseline_count}",
        f"Response samples: {event.response_count}",
        f"Baseline window: {event.baseline_start} to {event.baseline_end}",
        f"Response window: {event.response_start} to {event.response_end}",
        "",
    ]
    for key in METRIC_KEYS:
        lines.append(
            f"{METRIC_LABELS[key]}: {fmt(event.baseline_metrics.get(key))} -> {fmt(event.response_metrics.get(key))} "
            f"(Δ {fmt(event.delta_metrics.get(key))})"
        )
    lines.append(f"Artifact rate: {fmt(event.baseline_metrics.get('artifact_rate'), 2)} -> {fmt(event.response_metrics.get('artifact_rate'), 2)}")
    ax_text.text(
        0.02,
        0.98,
        "\n".join(lines),
        va="top",
        ha="left",
        family="monospace",
        fontsize=10,
        bbox={"facecolor": "#f8f9fa", "edgecolor": "#ced4da", "boxstyle": "round,pad=0.6"},
    )

    fig.suptitle(
        f"Spotify change response vs normal EEG baseline\n{event.to_track or 'unknown track'}",
        fontsize=15,
        fontweight="bold",
    )
    out_path = Path(event.screenshot_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def build_report(results: list[EventResult], session_sec: float) -> str:
    lines = [
        "Spotify EEG Change Monitor",
        f"session_seconds: {session_sec:.1f}",
        f"events_captured: {len(results)}",
        "",
    ]
    if not results:
        lines.append("No Spotify track-change events captured.")
        return "\n".join(lines) + "\n"
    for event in results:
        lines.extend(
            [
                f"[event_{event.event_index}]",
                f"changed_at: {event.changed_at}",
                f"from_track: {event.from_track or 'n/a'}",
                f"to_track: {event.to_track or 'n/a'}",
                f"from_frequency_hz: {fmt(event.from_frequency_hz, 1)}",
                f"to_frequency_hz: {fmt(event.to_frequency_hz, 1)}",
                f"baseline_eye_state: {event.baseline_eye_state or 'unknown'}",
                f"response_eye_state: {event.response_eye_state or 'unknown'}",
                f"baseline_count: {event.baseline_count}",
                f"response_count: {event.response_count}",
                f"screenshot_path: {event.screenshot_path}",
            ]
        )
        for key in METRIC_KEYS:
            lines.append(
                f"{key}: {fmt(event.baseline_metrics.get(key))} -> {fmt(event.response_metrics.get(key))} "
                f"(delta {fmt(event.delta_metrics.get(key))})"
            )
        lines.append(
            f"artifact_rate: {fmt(event.baseline_metrics.get('artifact_rate'), 2)} -> "
            f"{fmt(event.response_metrics.get('artifact_rate'), 2)} "
            f"(delta {fmt(event.delta_metrics.get('artifact_rate'), 2)})"
        )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    eeg_buffer: deque[EegState] = deque(maxlen=max(120, int((args.baseline_sec + args.response_sec + 30) / max(0.25, args.poll_sec))))
    results: list[EventResult] = []
    last_spotify: SpotifyState | None = None
    last_eeg_updated_at: str | None = None
    degraded_since: float | None = None
    last_quality_alert_at: float | None = None
    started = time.monotonic()

    while (time.monotonic() - started) < args.session_sec and len(results) < args.max_events:
        spotify = query_spotify()
        eeg = load_eeg_state(args.payload_path)
        eye_state = load_eye_state(args.eye_status_path)
        if eeg is not None and eeg.updated_at and eeg.updated_at != last_eeg_updated_at:
            eeg.eye_state = eye_state
            eeg_buffer.append(eeg)
            last_eeg_updated_at = eeg.updated_at
            now_unix = eeg.unix_time
            if eeg_quality_is_degraded(eeg):
                if degraded_since is None:
                    degraded_since = now_unix
                alert_due = (
                    (now_unix - degraded_since) >= args.quality_alert_sec
                    and (
                        last_quality_alert_at is None
                        or (now_unix - last_quality_alert_at) >= args.quality_alert_cooldown_sec
                    )
                )
                if alert_due:
                    play_sound(args.quality_alert_sound)
                    print(
                        f"{eeg.timestamp} quality_alert quality={eeg.quality or 'unknown'} "
                        f"artifact={'yes' if eeg.artifact_flag else 'no'}",
                        flush=True,
                    )
                    last_quality_alert_at = now_unix
            else:
                degraded_since = None

        track_changed = (
            last_spotify is not None
            and spotify.running
            and last_spotify.running
            and spotify.uri is not None
            and spotify.uri != last_spotify.uri
            and len(eeg_buffer) >= 3
        )
        if track_changed:
            changed_at = time.time()
            baseline_samples = [state for state in eeg_buffer if (changed_at - state.unix_time) <= args.baseline_sec]
            response_samples: list[EegState] = []
            response_seen: set[str] = set()
            wait_started = time.monotonic()
            while (time.monotonic() - wait_started) < args.response_sec:
                eeg_now = load_eeg_state(args.payload_path)
                if eeg_now is not None and eeg_now.updated_at and eeg_now.updated_at not in response_seen and eeg_now.updated_at != last_eeg_updated_at:
                    eeg_now.eye_state = load_eye_state(args.eye_status_path)
                    response_samples.append(eeg_now)
                    response_seen.add(eeg_now.updated_at)
                    eeg_buffer.append(eeg_now)
                    last_eeg_updated_at = eeg_now.updated_at
                time.sleep(max(0.2, args.poll_sec))

            baseline_metrics = summarise_states(baseline_samples)
            response_metrics = summarise_states(response_samples)
            deltas = delta_metrics(response_metrics, baseline_metrics)
            track_slug = slugify(spotify.track)
            time_slug = timestamp_slug(time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(changed_at)))
            screenshot_path = args.out_dir / f"spotify_eeg_event_{len(results) + 1:02d}_{time_slug}_{track_slug}.png"
            event = EventResult(
                event_index=len(results) + 1,
                changed_at=time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(changed_at)),
                baseline_start=baseline_samples[0].timestamp if baseline_samples else "",
                baseline_end=baseline_samples[-1].timestamp if baseline_samples else "",
                response_start=response_samples[0].timestamp if response_samples else "",
                response_end=response_samples[-1].timestamp if response_samples else "",
                from_track=last_spotify.track,
                to_track=spotify.track,
                from_artist=last_spotify.artist,
                to_artist=spotify.artist,
                from_uri=last_spotify.uri,
                to_uri=spotify.uri,
                from_frequency_hz=last_spotify.inferred_frequency_hz,
                to_frequency_hz=spotify.inferred_frequency_hz,
                baseline_count=len(baseline_samples),
                response_count=len(response_samples),
                baseline_eye_state=dominant_eye_state(baseline_samples),
                response_eye_state=dominant_eye_state(response_samples),
                baseline_metrics=baseline_metrics,
                response_metrics=response_metrics,
                delta_metrics=deltas,
                screenshot_path=str(screenshot_path),
            )
            make_screenshot(event, baseline_samples, response_samples)
            results.append(event)
            print(
                f"{event.changed_at} captured music change: "
                f"{event.from_track or 'n/a'} -> {event.to_track or 'n/a'} "
                f"| screenshot={event.screenshot_path}",
                flush=True,
            )
            last_spotify = spotify
            continue

        last_spotify = spotify
        time.sleep(max(0.2, args.poll_sec))

    report = build_report(results, time.monotonic() - started)
    args.summary_path.write_text(report)
    args.json_path.write_text(json.dumps([asdict(item) for item in results], indent=2))
    print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
