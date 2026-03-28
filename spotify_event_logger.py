#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path


DELIM = " ||| "


@dataclass
class SpotifySnapshot:
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Log interesting Spotify playback times from the local desktop app.")
    parser.add_argument("--poll-sec", type=float, default=1.0)
    parser.add_argument("--duration-sec", type=float, default=0.0, help="0 means run until stopped.")
    parser.add_argument("--stdout-mode", choices=["events", "heartbeat", "quiet"], default="events")
    parser.add_argument(
        "--status-path",
        type=Path,
        default=Path("/Users/simfish/Documents/GitHub/gaia-hackathon-2026/spotify_now_playing_status.txt"),
    )
    parser.add_argument(
        "--json-path",
        type=Path,
        default=Path("/Users/simfish/Documents/GitHub/gaia-hackathon-2026/spotify_now_playing_status.json"),
    )
    parser.add_argument(
        "--events-path",
        type=Path,
        default=Path("/Users/simfish/Documents/GitHub/gaia-hackathon-2026/spotify_interesting_times.jsonl"),
    )
    return parser.parse_args()


def now_stamp() -> tuple[str, float]:
    unix_time = time.time()
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(unix_time)), unix_time


def query_spotify() -> SpotifySnapshot:
    wall_time, unix_time = now_stamp()
    proc = subprocess.run(
        [
            "osascript",
            "-e",
            'if application "Spotify" is running then',
            "-e",
            f'tell application "Spotify" to return artist of current track & "{DELIM}" & name of current track & "{DELIM}" & album of current track & "{DELIM}" & id of current track & "{DELIM}" & (duration of current track as text) & "{DELIM}" & (player position as text) & "{DELIM}" & (player state as text)',
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
        return SpotifySnapshot(
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
        )

    parts = raw.split(DELIM)
    if len(parts) != 7:
        return SpotifySnapshot(
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
    return SpotifySnapshot(
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
    )


def format_status(snapshot: SpotifySnapshot) -> str:
    duration_sec = None if snapshot.duration_ms is None else snapshot.duration_ms / 1000.0
    remaining_sec = None
    if duration_sec is not None and snapshot.position_sec is not None:
        remaining_sec = max(0.0, duration_sec - snapshot.position_sec)

    def fmt(value: float | None) -> str:
        return "n/a" if value is None else f"{value:.1f}"

    return "\n".join(
        [
            "Spotify status",
            f"timestamp: {snapshot.timestamp}",
            f"running: {str(snapshot.running).lower()}",
            f"player_state: {snapshot.player_state}",
            f"artist: {snapshot.artist or 'n/a'}",
            f"track: {snapshot.track or 'n/a'}",
            f"album: {snapshot.album or 'n/a'}",
            f"uri: {snapshot.uri or 'n/a'}",
            f"position_sec: {fmt(snapshot.position_sec)}",
            f"duration_sec: {fmt(duration_sec)}",
            f"remaining_sec: {fmt(remaining_sec)}",
            "",
        ]
    )


def stdout_line(snapshot: SpotifySnapshot, events: list[str]) -> str:
    artist = snapshot.artist or "n/a"
    track = snapshot.track or "n/a"
    pos = "n/a" if snapshot.position_sec is None else f"{snapshot.position_sec:.1f}s"
    suffix = f" events={','.join(events)}" if events else ""
    return f"{snapshot.timestamp} state={snapshot.player_state} pos={pos} artist={artist} track={track}{suffix}"


def detect_events(curr: SpotifySnapshot, prev: SpotifySnapshot | None, poll_sec: float) -> list[str]:
    events: list[str] = []
    if prev is None:
        if curr.running:
            events.append("spotify_seen")
        return events

    if not prev.running and curr.running:
        events.append("spotify_started")
    if prev.running and not curr.running:
        events.append("spotify_stopped")
        return events

    if curr.uri != prev.uri and curr.running and curr.uri:
        events.append("track_changed")

    if prev.player_state != "playing" and curr.player_state == "playing":
        if prev.player_state == "paused":
            events.append("playback_resumed")
        else:
            events.append("playback_started")
    if prev.player_state == "playing" and curr.player_state == "paused":
        events.append("playback_paused")

    if curr.uri and prev.uri == curr.uri and prev.position_sec is not None and curr.position_sec is not None:
        delta = curr.position_sec - prev.position_sec
        if delta < -2.5:
            events.append("track_restarted")
        elif delta > max(5.0, poll_sec * 3.0):
            events.append("seek_jump_forward")
        elif delta < -max(5.0, poll_sec * 2.0):
            events.append("seek_jump_backward")

    if curr.duration_ms is not None and curr.position_sec is not None:
        remaining = curr.duration_ms / 1000.0 - curr.position_sec
        if remaining <= 10.0:
            events.append("track_near_end")

    return events


def main() -> int:
    args = parse_args()
    started = time.monotonic()
    previous: SpotifySnapshot | None = None
    args.events_path.parent.mkdir(parents=True, exist_ok=True)

    with args.events_path.open("a") as handle:
        while True:
            snapshot = query_spotify()
            events = detect_events(snapshot, previous, args.poll_sec)
            args.status_path.write_text(format_status(snapshot))
            args.json_path.write_text(json.dumps(asdict(snapshot), indent=2))

            if events:
                event_payload = {
                    "timestamp": snapshot.timestamp,
                    "unix_time": snapshot.unix_time,
                    "events": events,
                    "artist": snapshot.artist,
                    "track": snapshot.track,
                    "album": snapshot.album,
                    "uri": snapshot.uri,
                    "player_state": snapshot.player_state,
                    "position_sec": snapshot.position_sec,
                    "duration_ms": snapshot.duration_ms,
                }
                handle.write(json.dumps(event_payload) + "\n")
                handle.flush()

            if args.stdout_mode == "heartbeat":
                print(stdout_line(snapshot, events), flush=True)
            elif args.stdout_mode == "events" and events:
                print(stdout_line(snapshot, events), flush=True)

            previous = snapshot
            if args.duration_sec > 0 and (time.monotonic() - started) >= args.duration_sec:
                break
            time.sleep(max(0.1, args.poll_sec))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
