#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass
class EyeTrackStatus:
    timestamp: str
    unix_time: float
    face_detected: bool
    eyes_detected: int
    gaze_x: float | None
    gaze_y: float | None
    gaze_horizontal: str
    gaze_vertical: str
    confidence: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Coarse real-time webcam eye tracking.")
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=540)
    parser.add_argument("--fps", type=float, default=10.0)
    parser.add_argument("--display", action="store_true")
    parser.add_argument("--stdout-mode", choices=["heartbeat", "events", "quiet"], default="heartbeat")
    parser.add_argument("--duration-sec", type=float, default=0.0, help="0 means run until stopped.")
    parser.add_argument(
        "--status-path",
        type=Path,
        default=Path("/Users/simfish/Documents/GitHub/gaia-hackathon-2026/webcam_eye_status.txt"),
    )
    parser.add_argument(
        "--json-path",
        type=Path,
        default=Path("/Users/simfish/Documents/GitHub/gaia-hackathon-2026/webcam_eye_status.json"),
    )
    parser.add_argument(
        "--preview-path",
        type=Path,
        default=Path("/Users/simfish/Documents/GitHub/gaia-hackathon-2026/webcam_eye_preview.jpg"),
    )
    parser.add_argument(
        "--events-path",
        type=Path,
        default=Path("/Users/simfish/Documents/GitHub/gaia-hackathon-2026/webcam_eye_log.jsonl"),
    )
    return parser.parse_args()


def now_stamp() -> tuple[str, float]:
    unix_time = time.time()
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(unix_time)), unix_time


def format_status(status: EyeTrackStatus) -> str:
    def fmt(v: float | None) -> str:
        return "n/a" if v is None else f"{v:.3f}"

    return "\n".join(
        [
            "Webcam eye tracker status",
            f"timestamp: {status.timestamp}",
            f"face_detected: {str(status.face_detected).lower()}",
            f"eyes_detected: {status.eyes_detected}",
            f"gaze_x: {fmt(status.gaze_x)}",
            f"gaze_y: {fmt(status.gaze_y)}",
            f"gaze_horizontal: {status.gaze_horizontal}",
            f"gaze_vertical: {status.gaze_vertical}",
            f"confidence: {status.confidence:.3f}",
            "",
        ]
    )


def stdout_line(status: EyeTrackStatus) -> str:
    gx = "n/a" if status.gaze_x is None else f"{status.gaze_x:.2f}"
    gy = "n/a" if status.gaze_y is None else f"{status.gaze_y:.2f}"
    return (
        f"{status.timestamp} face={'yes' if status.face_detected else 'no'} eyes={status.eyes_detected} "
        f"gx={gx} gy={gy} hz={status.gaze_horizontal} vt={status.gaze_vertical} conf={status.confidence:.2f}"
    )


def should_print_event(curr: EyeTrackStatus, prev: EyeTrackStatus | None) -> bool:
    if prev is None:
        return True
    return (
        curr.gaze_horizontal != prev.gaze_horizontal
        or curr.gaze_vertical != prev.gaze_vertical
        or curr.eyes_detected != prev.eyes_detected
        or curr.face_detected != prev.face_detected
    )


def detect_primary_face(gray: np.ndarray, detector: cv2.CascadeClassifier) -> tuple[int, int, int, int] | None:
    faces = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(110, 110))
    if len(faces) == 0:
        return None
    x, y, w, h = max(faces, key=lambda item: item[2] * item[3])
    return int(x), int(y), int(w), int(h)


def pick_eyes(face_gray: np.ndarray, detector: cv2.CascadeClassifier) -> list[tuple[int, int, int, int]]:
    eyes = detector.detectMultiScale(face_gray, scaleFactor=1.08, minNeighbors=6, minSize=(26, 18))
    picked = []
    for ex, ey, ew, eh in eyes:
        if ey > face_gray.shape[0] * 0.62:
            continue
        picked.append((int(ex), int(ey), int(ew), int(eh)))
    picked.sort(key=lambda item: item[0])
    return picked[:2]


def pupil_ratio(eye_gray: np.ndarray) -> tuple[float | None, float | None, float]:
    if eye_gray.size == 0:
        return None, None, 0.0
    blur = cv2.GaussianBlur(eye_gray, (7, 7), 0)
    _, thresh = cv2.threshold(blur, int(np.percentile(blur, 18)), 255, cv2.THRESH_BINARY_INV)
    thresh = cv2.medianBlur(thresh, 5)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None, None, 0.0
    contour = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(contour)
    if area < eye_gray.size * 0.003:
        return None, None, 0.0
    moments = cv2.moments(contour)
    if moments["m00"] == 0:
        return None, None, 0.0
    cx = moments["m10"] / moments["m00"]
    cy = moments["m01"] / moments["m00"]
    return float(cx / eye_gray.shape[1]), float(cy / eye_gray.shape[0]), float(min(1.0, area / (eye_gray.size * 0.08)))


def gaze_labels(gaze_x: float | None, gaze_y: float | None) -> tuple[str, str]:
    if gaze_x is None or gaze_y is None:
        return "unknown", "unknown"
    if gaze_x < 0.42:
        horizontal = "left"
    elif gaze_x > 0.58:
        horizontal = "right"
    else:
        horizontal = "center"
    if gaze_y < 0.42:
        vertical = "up"
    elif gaze_y > 0.60:
        vertical = "down"
    else:
        vertical = "center"
    return horizontal, vertical


def main() -> int:
    args = parse_args()
    cap = cv2.VideoCapture(args.camera_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    cap.set(cv2.CAP_PROP_FPS, args.fps)
    if not cap.isOpened():
        raise SystemExit("Camera failed to open.")

    face_detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    eye_detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")
    started = time.monotonic()
    last_emit = 0.0
    last_printed: EyeTrackStatus | None = None
    args.events_path.parent.mkdir(parents=True, exist_ok=True)

    with args.events_path.open("a") as log_handle:
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.05)
                    continue
                frame = cv2.flip(frame, 1)
                frame_small = cv2.resize(frame, (args.width, args.height))
                gray = cv2.cvtColor(frame_small, cv2.COLOR_BGR2GRAY)
                gray = cv2.equalizeHist(gray)

                face_box = detect_primary_face(gray, face_detector)
                gaze_x: float | None = None
                gaze_y: float | None = None
                confidence = 0.0
                eyes_found = 0
                overlay = frame_small.copy()

                if face_box is not None:
                    x, y, w, h = face_box
                    cv2.rectangle(overlay, (x, y), (x + w, y + h), (255, 210, 120), 2)
                    face_gray = gray[y : y + h, x : x + w]
                    eyes = pick_eyes(face_gray, eye_detector)
                    eyes_found = len(eyes)
                    xs: list[float] = []
                    ys: list[float] = []
                    confs: list[float] = []
                    for ex, ey, ew, eh in eyes:
                        cv2.rectangle(overlay, (x + ex, y + ey), (x + ex + ew, y + ey + eh), (0, 255, 0), 2)
                        eye_roi = face_gray[ey : ey + eh, ex : ex + ew]
                        px, py, conf = pupil_ratio(eye_roi)
                        if px is not None and py is not None:
                            xs.append(px)
                            ys.append(py)
                            confs.append(conf)
                            cx = int(x + ex + px * ew)
                            cy = int(y + ey + py * eh)
                            cv2.circle(overlay, (cx, cy), 4, (0, 0, 255), -1)
                    if xs and ys:
                        gaze_x = float(np.mean(xs))
                        gaze_y = float(np.mean(ys))
                        confidence = float(np.mean(confs)) if confs else 0.0

                hz, vt = gaze_labels(gaze_x, gaze_y)
                wall_time, unix_time = now_stamp()
                status = EyeTrackStatus(
                    timestamp=wall_time,
                    unix_time=unix_time,
                    face_detected=face_box is not None,
                    eyes_detected=eyes_found,
                    gaze_x=gaze_x,
                    gaze_y=gaze_y,
                    gaze_horizontal=hz,
                    gaze_vertical=vt,
                    confidence=confidence,
                )

                text = f"{hz}/{vt} eyes={eyes_found} conf={confidence:.2f}"
                cv2.putText(overlay, text, (14, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 2, cv2.LINE_AA)

                now_mono = time.monotonic()
                if (now_mono - last_emit) >= max(0.1, 1.0 / args.fps):
                    args.status_path.write_text(format_status(status))
                    args.json_path.write_text(json.dumps(asdict(status), indent=2))
                    cv2.imwrite(str(args.preview_path), overlay)
                    log_handle.write(json.dumps(asdict(status)) + "\n")
                    log_handle.flush()
                    if args.stdout_mode == "heartbeat":
                        print(stdout_line(status), flush=True)
                    elif args.stdout_mode == "events" and should_print_event(status, last_printed):
                        print(stdout_line(status), flush=True)
                    last_printed = status
                    last_emit = now_mono

                if args.display:
                    cv2.imshow("Webcam Eye Tracker", overlay)
                    key = cv2.waitKey(1) & 0xFF
                    if key in (ord("q"), 27):
                        break

                if args.duration_sec > 0 and (time.monotonic() - started) >= args.duration_sec:
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
