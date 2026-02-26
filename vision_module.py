"""
SafeGuard Sentinel — Vision Module
Handles real-time human/obstacle detection using YOLOv8 + OpenCV.
Falls back to simulation mode if no camera is available.
"""

import cv2
import numpy as np
import time
import random
from dataclasses import dataclass, field
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Try to import ultralytics; gracefully degrade if not installed
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    logger.warning("ultralytics not installed — running in simulation mode")


# ─────────────────────────────────────────────
#  Data Structures
# ─────────────────────────────────────────────

@dataclass
class Detection:
    label: str
    confidence: float
    bbox: tuple          # (x1, y1, x2, y2) normalized 0-1
    distance_estimate: str  # "near" | "mid" | "far"
    is_human: bool


@dataclass
class SceneSnapshot:
    timestamp: float
    detections: list[Detection] = field(default_factory=list)
    human_count: int = 0
    obstacle_count: int = 0
    nearest_human_distance: Optional[str] = None   # "near" | "mid" | "far" | None
    frame_base64: Optional[str] = None             # JPEG base64 for dashboard


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

HUMAN_LABELS = {"person"}
OBSTACLE_LABELS = {"chair", "table", "bottle", "cup", "laptop", "keyboard",
                   "cell phone", "book", "vase", "scissors", "teddy bear",
                   "car", "truck", "bicycle", "motorcycle", "bus", "stop sign",
                   "fire hydrant", "potted plant", "suitcase", "backpack"}

DISTANCE_ZONES = {
    # bbox area thresholds (fraction of frame)
    "near": 0.15,   # > 15% of frame → very close
    "mid":  0.04,   # 4-15% → moderate distance
    "far":  0.0,    # < 4% → far away
}


def _estimate_distance(bbox: tuple) -> str:
    x1, y1, x2, y2 = bbox
    area = (x2 - x1) * (y2 - y1)  # already normalized
    if area >= DISTANCE_ZONES["near"]:
        return "near"
    elif area >= DISTANCE_ZONES["mid"]:
        return "mid"
    return "far"


def _frame_to_base64(frame: np.ndarray) -> str:
    import base64
    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
    return base64.b64encode(buf).decode("utf-8")


def _annotate_frame(frame: np.ndarray, detections: list[Detection]) -> np.ndarray:
    """Draw bounding boxes and labels on the frame."""
    h, w = frame.shape[:2]
    for det in detections:
        x1, y1, x2, y2 = det.bbox
        px1, py1 = int(x1 * w), int(y1 * h)
        px2, py2 = int(x2 * w), int(y2 * h)
        color = (0, 0, 220) if det.is_human else (0, 165, 255)
        cv2.rectangle(frame, (px1, py1), (px2, py2), color, 2)
        label_text = f"{det.label} {det.confidence:.0%} [{det.distance_estimate}]"
        cv2.putText(frame, label_text, (px1, py1 - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
    # Watermark
    cv2.putText(frame, "SafeGuard Sentinel", (10, h - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)
    return frame


# ─────────────────────────────────────────────
#  Simulation Mode
# ─────────────────────────────────────────────

def _generate_sim_frame(detections: list[Detection]) -> np.ndarray:
    """Creates a fake 640×480 scene for demo purposes."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[:] = (30, 30, 30)
    # draw grid lines
    for x in range(0, 640, 80):
        cv2.line(frame, (x, 0), (x, 480), (45, 45, 45), 1)
    for y in range(0, 480, 60):
        cv2.line(frame, (0, y), (640, y), (45, 45, 45), 1)
    return _annotate_frame(frame, detections)


SIM_SCENARIOS = [
    # (label, confidence, bbox, is_human)
    lambda: [Detection("person", random.uniform(0.82, 0.97),
                        (0.3, 0.2, 0.55, 0.8), "near", True)],
    lambda: [Detection("person", random.uniform(0.78, 0.92),
                        (0.6, 0.3, 0.75, 0.7), "mid", True),
             Detection("chair", random.uniform(0.6, 0.8),
                        (0.1, 0.5, 0.28, 0.9), "mid", False)],
    lambda: [],  # clear scene
    lambda: [Detection("person", random.uniform(0.88, 0.99),
                        (0.42, 0.1, 0.58, 0.9), "near", True),
             Detection("person", random.uniform(0.75, 0.88),
                        (0.65, 0.25, 0.8, 0.75), "mid", True)],
    lambda: [Detection("car", random.uniform(0.7, 0.9),
                        (0.05, 0.4, 0.4, 0.85), "near", False)],
]

_sim_scenario_idx = 0
_sim_last_change = 0.0


def _simulate_detections() -> list[Detection]:
    global _sim_scenario_idx, _sim_last_change
    now = time.time()
    if now - _sim_last_change > random.uniform(4, 8):
        _sim_scenario_idx = random.randint(0, len(SIM_SCENARIOS) - 1)
        _sim_last_change = now
    return SIM_SCENARIOS[_sim_scenario_idx]()


# ─────────────────────────────────────────────
#  Main Vision Engine
# ─────────────────────────────────────────────

class VisionEngine:
    """
    Wraps YOLO inference (or simulation) and outputs SceneSnapshot objects.
    Usage:
        engine = VisionEngine()
        snapshot = engine.capture()
    """

    def __init__(self, camera_index: int = 0,
                 model_path: str = "yolov8n.pt",
                 force_simulation: bool = False,
                 confidence_threshold: float = 0.45):
        self.simulation = force_simulation or not YOLO_AVAILABLE
        self.confidence_threshold = confidence_threshold
        self.cap: Optional[cv2.VideoCapture] = None
        self.model = None

        if not self.simulation:
            self._init_camera(camera_index)
            self._init_model(model_path)

        mode = "SIMULATION" if self.simulation else "LIVE"
        logger.info(f"VisionEngine initialized in {mode} mode")

    def _init_camera(self, index: int):
        self.cap = cv2.VideoCapture(index)
        if not self.cap.isOpened():
            logger.warning(f"Camera {index} unavailable — switching to simulation")
            self.simulation = True
            self.cap = None
        else:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    def _init_model(self, path: str):
        try:
            self.model = YOLO(path)
            logger.info(f"YOLOv8 model loaded: {path}")
        except Exception as e:
            logger.warning(f"Failed to load YOLO model ({e}) — simulation mode")
            self.simulation = True

    # ------------------------------------------------------------------

    def capture(self) -> SceneSnapshot:
        """Main entry point: returns a full SceneSnapshot."""
        if self.simulation:
            return self._capture_simulated()
        return self._capture_live()

    def _capture_simulated(self) -> SceneSnapshot:
        detections = _simulate_detections()
        frame = _generate_sim_frame(detections)
        return self._build_snapshot(detections, frame)

    def _capture_live(self) -> SceneSnapshot:
        ret, frame = self.cap.read()
        if not ret:
            logger.warning("Failed to read frame — falling back to simulation")
            return self._capture_simulated()

        results = self.model(frame, verbose=False)[0]
        detections = []
        for box in results.boxes:
            conf = float(box.conf[0])
            if conf < self.confidence_threshold:
                continue
            cls_id = int(box.cls[0])
            label = self.model.names[cls_id]
            h, w = frame.shape[:2]
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            norm_bbox = (x1 / w, y1 / h, x2 / w, y2 / h)
            is_human = label in HUMAN_LABELS
            detections.append(Detection(
                label=label,
                confidence=conf,
                bbox=norm_bbox,
                distance_estimate=_estimate_distance(norm_bbox),
                is_human=is_human,
            ))

        annotated = _annotate_frame(frame.copy(), detections)
        return self._build_snapshot(detections, annotated)

    def _build_snapshot(self, detections: list[Detection],
                        frame: np.ndarray) -> SceneSnapshot:
        humans = [d for d in detections if d.is_human]
        obstacles = [d for d in detections if not d.is_human]
        nearest = None
        if humans:
            order = {"near": 0, "mid": 1, "far": 2}
            nearest = min(humans, key=lambda d: order[d.distance_estimate]).distance_estimate

        return SceneSnapshot(
            timestamp=time.time(),
            detections=detections,
            human_count=len(humans),
            obstacle_count=len(obstacles),
            nearest_human_distance=nearest,
            frame_base64=_frame_to_base64(frame),
        )

    def release(self):
        if self.cap:
            self.cap.release()
