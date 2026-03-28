#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Push the local OpenBCI OpenBCI status text and live JSON online.")
    parser.add_argument("--status-path", type=Path, default=Path("/Users/simfish/Documents/GitHub/gaia-hackathon-2026/openbci_live_status.txt"))
    parser.add_argument("--payload-path", type=Path, default=Path("/Users/simfish/Documents/GitHub/gaia-hackathon-2026/openbci_live_payload.json"))
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
                body = args.payload_path.read_text()
                digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
                if digest != last_payload_digest:
                    try:
                        json.loads(body)
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
