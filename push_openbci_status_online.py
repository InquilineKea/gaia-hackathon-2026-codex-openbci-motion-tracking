#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

SPOTIFY_DELIM = " ||| "


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Push the local OpenBCI OpenBCI status text and live JSON online.")
    parser.add_argument("--status-path", type=Path, default=Path("/Users/simfish/Documents/GitHub/gaia-hackathon-2026/openbci_live_status.txt"))
    parser.add_argument("--payload-path", type=Path, default=Path("/Users/simfish/Documents/GitHub/gaia-hackathon-2026/openbci_live_payload.json"))
    parser.add_argument(
        "--spotify-status-path",
        type=Path,
        default=Path("/Users/simfish/Documents/GitHub/gaia-hackathon-2026/spotify_now_playing_status.json"),
        help="Optional Spotify status JSON to attach to the live payload.",
    )
    parser.add_argument(
        "--spotify-max-age-sec",
        type=float,
        default=15.0,
        help="Treat the Spotify status JSON as stale after this many seconds and query Spotify directly.",
    )
    parser.add_argument("--url", help="Legacy alias for --status-url.")
    parser.add_argument("--status-url", help="Worker /update URL.")
    parser.add_argument("--live-url", help="Worker /live URL.")
    parser.add_argument("--token", required=True, help="Bearer token expected by the Worker.")
    parser.add_argument("--interval-sec", type=float, default=1.0)
    parser.add_argument("--duration-sec", type=float, default=0.0, help="0 means run until Ctrl-C.")
    return parser.parse_args()


def push_body(url: str, token: str, body: bytes, content_type: str) -> None:
    result = subprocess.run(
        [
            "curl",
            "-fsS",
            "-X",
            "POST",
            url,
            "-H",
            f"Authorization: Bearer {token}",
            "-H",
            f"Content-Type: {content_type}",
            "--data-binary",
            "@-",
        ],
        input=body,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(stderr or f"curl failed with code {result.returncode}")
    if result.stdout:
        sys.stdout.write(result.stdout.decode("utf-8"))
        sys.stdout.flush()


def query_spotify_direct() -> dict | None:
    unix_time = time.time()
    wall_time = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(unix_time))
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
        return None
    parts = [part.strip() for part in raw.split(SPOTIFY_DELIM)]
    if len(parts) != 7:
        return None
    artist, track, album, uri, duration_text, position_text, player_state = parts
    try:
        duration_ms = int(float(duration_text))
    except ValueError:
        duration_ms = None
    try:
        position_sec = float(position_text)
    except ValueError:
        position_sec = None
    return {
        "timestamp": wall_time,
        "unix_time": unix_time,
        "running": True,
        "player_state": player_state,
        "artist": artist or None,
        "track": track or None,
        "album": album or None,
        "uri": uri or None,
        "duration_ms": duration_ms,
        "position_sec": position_sec,
        "source": "direct_query",
    }


def load_spotify_status(path: Path, max_age_sec: float) -> dict | None:
    if path.exists():
        age_sec = max(0.0, time.time() - path.stat().st_mtime)
        if age_sec <= max_age_sec:
            try:
                payload = json.loads(path.read_text())
            except Exception:
                payload = None
            if isinstance(payload, dict):
                return payload
    direct = query_spotify_direct()
    if direct:
        try:
            path.write_text(json.dumps(direct, indent=2))
        except Exception:
            pass
        return direct
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text())
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def main() -> int:
    args = parse_args()
    status_url = args.status_url or args.url
    live_url = args.live_url
    last_status_digest = None
    last_payload_digest = None
    started = time.monotonic()

    try:
        while True:
            if args.payload_path.exists() and live_url:
                raw_body = args.payload_path.read_text()
                try:
                    payload = json.loads(raw_body)
                    spotify = load_spotify_status(args.spotify_status_path, args.spotify_max_age_sec)
                    if spotify:
                        payload["spotify"] = spotify
                    body = json.dumps(payload, separators=(",", ":"))
                    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
                    if digest != last_payload_digest:
                        push_body(
                            live_url,
                            args.token,
                            body.encode("utf-8"),
                            "application/json; charset=utf-8",
                        )
                        last_payload_digest = digest
                except (json.JSONDecodeError, RuntimeError) as exc:
                    print(f"payload push failed: {exc}", file=sys.stderr)

            if args.status_path.exists() and status_url:
                body = args.status_path.read_text()
                digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
                if digest != last_status_digest:
                    try:
                        push_body(
                            status_url,
                            args.token,
                            body.encode("utf-8"),
                            "text/plain; charset=utf-8",
                        )
                        last_status_digest = digest
                    except RuntimeError as exc:
                        print(f"push failed: {exc}", file=sys.stderr)

            if args.duration_sec > 0 and (time.monotonic() - started) >= args.duration_sec:
                break
            time.sleep(args.interval_sec)
    except KeyboardInterrupt:
        pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
