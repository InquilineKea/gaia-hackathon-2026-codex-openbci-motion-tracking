#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import time
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass
class EventSnapshot:
    timestamp: str
    unix_time: float
    motion_score: float
    skin_score: float
    hand_candidate_count: int
    held_object_candidate: bool
    unusual_motion: bool
    activity_level: str
    event_tags: list[str]
    face_detected: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Heuristic webcam event tagger for hands, held-object candidates, and unusual motion.")
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=540)
    parser.add_argument("--fps", type=float, default=10.0)
    parser.add_argument("--display", action="store_true")
    parser.add_argument("--duration-sec", type=float, default=0.0, help="0 means run until q/Ctrl-C.")
    parser.add_argument("--stdout-mode", choices=["events", "heartbeat", "quiet"], default="events")
    parser.add_argument(
        "--electrode-labels",
        default="BIAS,L-FRONT,L-MID,L-LOW,CROWN,R-FRONT,R-MID,R-LOW,BACK",
        help="Comma-separated approximate overlay labels, first label used for left-most bias point.",
    )
    parser.add_argument("--status-path", type=Path, default=Path("/Users/simfish/Documents/GitHub/gaia-hackathon-2026/webcam_event_status.txt"))
    parser.add_argument("--json-path", type=Path, default=Path("/Users/simfish/Documents/GitHub/gaia-hackathon-2026/webcam_event_status.json"))
    parser.add_argument("--events-path", type=Path, default=Path("/Users/simfish/Documents/GitHub/gaia-hackathon-2026/webcam_event_log.jsonl"))
    parser.add_argument("--preview-path", type=Path, default=Path("/Users/simfish/Documents/GitHub/gaia-hackathon-2026/webcam_event_preview.jpg"))
    return parser.parse_args()


def now_stamp() -> tuple[str, float]:
    unix_time = time.time()
    wall_time = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(unix_time))
    return wall_time, unix_time


def make_status_text(snapshot: EventSnapshot) -> str:
    return "\n".join(
        [
            "Webcam event tagger status",
            f"timestamp: {snapshot.timestamp}",
            f"face_detected: {str(snapshot.face_detected).lower()}",
            f"motion_score: {snapshot.motion_score:.4f}",
            f"skin_score: {snapshot.skin_score:.4f}",
            f"hand_candidate_count: {snapshot.hand_candidate_count}",
            f"held_object_candidate: {str(snapshot.held_object_candidate).lower()}",
            f"unusual_motion: {str(snapshot.unusual_motion).lower()}",
            f"activity_level: {snapshot.activity_level}",
            f"event_tags: {', '.join(snapshot.event_tags) if snapshot.event_tags else 'none'}",
            "",
        ]
    )


def make_stdout_line(snapshot: EventSnapshot) -> str:
    tags = ",".join(snapshot.event_tags) if snapshot.event_tags else "none"
    return (
        f"{snapshot.timestamp} "
        f"face={'yes' if snapshot.face_detected else 'no'} "
        f"motion={snapshot.motion_score:.4f} "
        f"skin={snapshot.skin_score:.4f} "
        f"hands={snapshot.hand_candidate_count} "
        f"held={'yes' if snapshot.held_object_candidate else 'no'} "
        f"weird={'yes' if snapshot.unusual_motion else 'no'} "
        f"level={snapshot.activity_level} "
        f"tags={tags}"
    )


def should_print_event(snapshot: EventSnapshot, previous: EventSnapshot | None) -> bool:
    interesting_tags = {"held_object_candidate", "unusual_motion", "high_motion", "multiple_hand_candidates"}
    if any(tag in interesting_tags for tag in snapshot.event_tags):
        return True
    if previous is None:
        return True
    if snapshot.hand_candidate_count != previous.hand_candidate_count:
        return True
    if snapshot.activity_level != previous.activity_level:
        return True
    if snapshot.event_tags != previous.event_tags:
        return True
    return False


def contour_boxes(mask: np.ndarray, min_area: float) -> list[tuple[int, int, int, int, float]]:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        boxes.append((x, y, w, h, float(area)))
    return boxes


def detect_primary_face(gray: np.ndarray, face_detector: cv2.CascadeClassifier) -> tuple[int, int, int, int] | None:
    faces = face_detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100))
    if len(faces) == 0:
        return None
    x, y, w, h = max(faces, key=lambda item: item[2] * item[3])
    return int(x), int(y), int(w), int(h)


def electrode_points(face_box: tuple[int, int, int, int], labels: list[str]) -> list[tuple[str, tuple[int, int]]]:
    x, y, w, h = face_box
    base_points = [
        (x - int(0.18 * w), y + int(0.28 * h)),  # bias left of face
        (x + int(0.06 * w), y + int(0.05 * h)),
        (x - int(0.02 * w), y + int(0.32 * h)),
        (x + int(0.02 * w), y + int(0.70 * h)),
        (x + int(0.50 * w), y - int(0.12 * h)),
        (x + int(0.94 * w), y + int(0.05 * h)),
        (x + int(1.02 * w), y + int(0.32 * h)),
        (x + int(0.98 * w), y + int(0.70 * h)),
        (x + int(0.50 * w), y + int(0.98 * h)),
    ]
    trimmed_labels = labels[: len(base_points)]
    return [(label, point) for label, point in zip(trimmed_labels, base_points)]


def draw_electrode_overlay(frame: np.ndarray, face_box: tuple[int, int, int, int] | None, labels: list[str]) -> bool:
    if face_box is None:
        return False
    x, y, w, h = face_box
    cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 210, 120), 2)
    for label, (px, py) in electrode_points(face_box, labels):
        cv2.circle(frame, (px, py), 6, (255, 255, 0), -1)
        tx = px + 8
        ty = py - 6
        cv2.line(frame, (px, py), (tx, ty), (255, 255, 0), 1)
        cv2.putText(frame, label, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 0), 1, cv2.LINE_AA)
    return True


def intersection_over_union(a: tuple[int, int, int, int, float], b: tuple[int, int, int, int, float]) -> float:
    ax, ay, aw, ah, _ = a
    bx, by, bw, bh, _ = b
    x1 = max(ax, bx)
    y1 = max(ay, by)
    x2 = min(ax + aw, bx + bw)
    y2 = min(ay + ah, by + bh)
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    if inter <= 0:
        return 0.0
    area_a = aw * ah
    area_b = bw * bh
    return inter / float(area_a + area_b - inter)


def classify_activity(motion_score: float, hand_count: int, held_object: bool, unusual_motion: bool) -> tuple[str, list[str]]:
    tags: list[str] = []
    if hand_count > 0:
        tags.append("hand_present")
    if hand_count >= 2:
        tags.append("multiple_hand_candidates")
    if held_object:
        tags.append("held_object_candidate")
    if unusual_motion:
        tags.append("unusual_motion")
    if motion_score > 0.18:
        tags.append("high_motion")

    if unusual_motion or held_object:
        return "interesting", tags
    if hand_count > 0 or motion_score > 0.05:
        return "active", tags
    return "idle", tags


def main() -> int:
    args = parse_args()
    electrode_labels = [item.strip() for item in args.electrode_labels.split(",") if item.strip()]
    cap = cv2.VideoCapture(args.camera_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    cap.set(cv2.CAP_PROP_FPS, args.fps)

    if not cap.isOpened():
        raise SystemExit("Camera failed to open. Grant camera access to Python/Terminal in macOS and rerun.")

    face_detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    subtractor = cv2.createBackgroundSubtractorMOG2(history=200, varThreshold=32, detectShadows=False)
    motion_history: deque[float] = deque(maxlen=max(8, int(args.fps * 2)))
    last_emit = 0.0
    last_printed_snapshot: EventSnapshot | None = None
    started = time.monotonic()

    args.events_path.parent.mkdir(parents=True, exist_ok=True)
    events_handle = args.events_path.open("a")

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.05)
                continue

            frame = cv2.flip(frame, 1)
            frame_small = cv2.resize(frame, (args.width, args.height))
            gray = cv2.cvtColor(frame_small, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (5, 5), 0)
            face_box = detect_primary_face(gray, face_detector)
            fg_mask = subtractor.apply(frame_small)
            _, fg_mask = cv2.threshold(fg_mask, 210, 255, cv2.THRESH_BINARY)
            fg_mask = cv2.medianBlur(fg_mask, 5)

            ycrcb = cv2.cvtColor(frame_small, cv2.COLOR_BGR2YCrCb)
            lower = np.array([0, 135, 85], dtype=np.uint8)
            upper = np.array([255, 180, 135], dtype=np.uint8)
            skin_mask = cv2.inRange(ycrcb, lower, upper)
            skin_mask = cv2.GaussianBlur(skin_mask, (5, 5), 0)
            _, skin_mask = cv2.threshold(skin_mask, 120, 255, cv2.THRESH_BINARY)

            h, w = gray.shape
            lower_focus = np.zeros_like(gray)
            lower_focus[int(h * 0.20):, :] = 255
            fg_mask = cv2.bitwise_and(fg_mask, lower_focus)
            skin_mask = cv2.bitwise_and(skin_mask, lower_focus)

            motion_boxes = contour_boxes(fg_mask, min_area=w * h * 0.004)
            skin_boxes = contour_boxes(skin_mask, min_area=w * h * 0.0025)

            motion_score = float(np.count_nonzero(fg_mask) / float(fg_mask.size))
            skin_score = float(np.count_nonzero(skin_mask) / float(skin_mask.size))
            motion_history.append(motion_score)

            unusual_motion = False
            if len(motion_history) >= 5:
                baseline = np.median(np.asarray(motion_history, dtype=float))
                unusual_motion = motion_score > max(0.12, baseline * 1.9)

            held_object_candidate = False
            for skin_box in skin_boxes:
                sx, sy, sw, sh, _ = skin_box
                pad = 18
                x1 = max(0, sx - pad)
                y1 = max(0, sy - pad)
                x2 = min(w, sx + sw + pad)
                y2 = min(h, sy + sh + pad)
                roi = frame_small[y1:y2, x1:x2]
                if roi.size == 0:
                    continue
                roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                edges = cv2.Canny(roi_gray, 60, 140)
                edge_density = float(np.count_nonzero(edges) / float(edges.size))
                overlap = max((intersection_over_union(skin_box, motion_box) for motion_box in motion_boxes), default=0.0)
                if overlap > 0.18 and edge_density > 0.06 and (sw * sh) > (w * h * 0.012):
                    held_object_candidate = True
                    break

            activity_level, tags = classify_activity(
                motion_score=motion_score,
                hand_count=len(skin_boxes),
                held_object=held_object_candidate,
                unusual_motion=unusual_motion,
            )

            wall_time, unix_time = now_stamp()
            snapshot = EventSnapshot(
                timestamp=wall_time,
                unix_time=unix_time,
                motion_score=motion_score,
                skin_score=skin_score,
                hand_candidate_count=len(skin_boxes),
                held_object_candidate=held_object_candidate,
                unusual_motion=unusual_motion,
                activity_level=activity_level,
                event_tags=tags,
                face_detected=face_box is not None,
            )

            overlay = frame_small.copy()
            for x, y, bw, bh, _ in motion_boxes:
                cv2.rectangle(overlay, (x, y), (x + bw, y + bh), (0, 180, 255), 2)
            for x, y, bw, bh, _ in skin_boxes:
                cv2.rectangle(overlay, (x, y), (x + bw, y + bh), (0, 255, 0), 2)
            text = f"{activity_level}  hands={len(skin_boxes)}  held={int(held_object_candidate)}  weird={int(unusual_motion)}"
            cv2.putText(overlay, text, (14, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 2, cv2.LINE_AA)
            draw_electrode_overlay(overlay, face_box, electrode_labels)

            now_mono = time.monotonic()
            if (now_mono - last_emit) >= max(0.1, 1.0 / args.fps):
                args.status_path.write_text(make_status_text(snapshot))
                args.json_path.write_text(json.dumps(asdict(snapshot), indent=2))
                events_handle.write(json.dumps(asdict(snapshot)) + "\n")
                events_handle.flush()
                cv2.imwrite(str(args.preview_path), overlay)
                if args.stdout_mode == "heartbeat":
                    print(make_stdout_line(snapshot), flush=True)
                elif args.stdout_mode == "events" and should_print_event(snapshot, last_printed_snapshot):
                    print(make_stdout_line(snapshot), flush=True)
                last_printed_snapshot = snapshot
                last_emit = now_mono

            if args.display:
                cv2.imshow("Webcam Event Tagger", overlay)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):
                    break

            if args.duration_sec > 0 and (time.monotonic() - started) >= args.duration_sec:
                break
    finally:
        events_handle.close()
        cap.release()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
