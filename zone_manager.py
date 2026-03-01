"""
SafeGuard Sentinel — Zone Manager
Defines spatial zones on the camera frame (normalized 0-1 coords).
Each zone has a type: RESTRICTED, WARNING, or SAFE.

Zones are checked against detections to add spatial context to
the Safety Policy Engine's risk evaluation.

Zone format: {"id", "name", "type", "bbox": (x1,y1,x2,y2), "color_bgr"}
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import json
import os
import cv2
import numpy as np

# ─────────────────────────────────────────────
#  Zone Types
# ─────────────────────────────────────────────

class ZoneType(str, Enum):
    RESTRICTED = "RESTRICTED"   # Robot must never enter / act here
    WARNING    = "WARNING"      # Elevated caution required
    SAFE       = "SAFE"         # Designated safe operating area


ZONE_COLORS = {
    ZoneType.RESTRICTED: (0,   40, 220),   # Red (BGR)
    ZoneType.WARNING:    (0,  165, 245),   # Orange
    ZoneType.SAFE:       (80, 200,  80),   # Green
}

ZONE_RISK_MULTIPLIERS = {
    ZoneType.RESTRICTED: 2.0,
    ZoneType.WARNING:    1.4,
    ZoneType.SAFE:       0.6,
}


# ─────────────────────────────────────────────
#  Data Structures
# ─────────────────────────────────────────────

@dataclass
class Zone:
    id:       str
    name:     str
    type:     ZoneType
    bbox:     tuple           # (x1, y1, x2, y2) normalized 0-1
    enabled:  bool = True

    def contains_point(self, x: float, y: float) -> bool:
        x1, y1, x2, y2 = self.bbox
        return x1 <= x <= x2 and y1 <= y <= y2

    def overlaps_bbox(self, bbox: tuple) -> bool:
        """Returns True if the given bbox overlaps this zone."""
        ax1, ay1, ax2, ay2 = self.bbox
        bx1, by1, bx2, by2 = bbox
        return not (bx2 < ax1 or bx1 > ax2 or by2 < ay1 or by1 > ay2)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "type": self.type,
            "bbox": list(self.bbox), "enabled": self.enabled,
        }

    @staticmethod
    def from_dict(d: dict) -> "Zone":
        return Zone(
            id=d["id"], name=d["name"],
            type=ZoneType(d["type"]),
            bbox=tuple(d["bbox"]),
            enabled=d.get("enabled", True),
        )


@dataclass
class ZoneViolation:
    zone: Zone
    detection_label: str
    is_human: bool


@dataclass
class ZoneAnalysis:
    active_zones:       list[Zone]
    zone_violations:    list[ZoneViolation]   # humans/obstacles in restricted zones
    risk_multiplier:    float                  # net multiplier to apply to base risk
    summary:            str
    annotated_frame:    Optional[np.ndarray] = None


# ─────────────────────────────────────────────
#  Zone Manager
# ─────────────────────────────────────────────

ZONES_FILE = "zones.json"

DEFAULT_ZONES = [
    Zone("z1", "Left Restricted Area",    ZoneType.RESTRICTED, (0.0,  0.0,  0.25, 1.0)),
    Zone("z2", "Right Restricted Area",   ZoneType.RESTRICTED, (0.75, 0.0,  1.0,  1.0)),
    Zone("z3", "Center Warning Corridor", ZoneType.WARNING,    (0.25, 0.0,  0.75, 0.5)),
    Zone("z4", "Safe Operating Zone",     ZoneType.SAFE,       (0.25, 0.5,  0.75, 1.0)),
]


class ZoneManager:
    """
    Manages spatial zones, persists them to disk, and evaluates
    detections against zones to produce a ZoneAnalysis.
    """

    def __init__(self, zones_file: str = ZONES_FILE):
        self.zones_file = zones_file
        self.zones: list[Zone] = []
        self._load()

    # ── Persistence ───────────────────────────────────────────────────

    def _load(self):
        if os.path.exists(self.zones_file):
            try:
                with open(self.zones_file) as f:
                    data = json.load(f)
                self.zones = [Zone.from_dict(z) for z in data]
                return
            except Exception:
                pass
        self.zones = list(DEFAULT_ZONES)
        self._save()

    def _save(self):
        with open(self.zones_file, "w") as f:
            json.dump([z.to_dict() for z in self.zones], f, indent=2)

    # ── CRUD ──────────────────────────────────────────────────────────

    def add_zone(self, name: str, zone_type: ZoneType, bbox: tuple) -> Zone:
        zone_id = f"z{len(self.zones) + 1}_{int(bbox[0]*100)}"
        zone = Zone(id=zone_id, name=name, type=zone_type, bbox=bbox)
        self.zones.append(zone)
        self._save()
        return zone

    def remove_zone(self, zone_id: str) -> bool:
        before = len(self.zones)
        self.zones = [z for z in self.zones if z.id != zone_id]
        if len(self.zones) < before:
            self._save()
            return True
        return False

    def toggle_zone(self, zone_id: str) -> Optional[Zone]:
        for z in self.zones:
            if z.id == zone_id:
                z.enabled = not z.enabled
                self._save()
                return z
        return None

    def reset_to_defaults(self):
        self.zones = list(DEFAULT_ZONES)
        self._save()

    def get_active_zones(self) -> list[Zone]:
        return [z for z in self.zones if z.enabled]

    # ── Core Analysis ─────────────────────────────────────────────────

    def analyze(self, detections: list, frame: Optional[np.ndarray] = None) -> ZoneAnalysis:
        """
        Check all detections against active zones.
        Returns ZoneAnalysis with violations and risk multiplier.
        detections: list of Detection objects from vision_module
        """
        active = self.get_active_zones()
        violations: list[ZoneViolation] = []
        worst_multiplier = 1.0

        for det in detections:
            det_center_x = (det.bbox[0] + det.bbox[2]) / 2
            det_center_y = (det.bbox[1] + det.bbox[3]) / 2

            for zone in active:
                if zone.overlaps_bbox(det.bbox):
                    multiplier = ZONE_RISK_MULTIPLIERS[zone.type]
                    worst_multiplier = max(worst_multiplier, multiplier)

                    if zone.type == ZoneType.RESTRICTED:
                        violations.append(ZoneViolation(
                            zone=zone,
                            detection_label=det.label,
                            is_human=det.is_human,
                        ))

        # Build summary
        if violations:
            labels = [f"{'HUMAN' if v.is_human else v.detection_label} in {v.zone.name}"
                      for v in violations]
            summary = f"Zone violations: {'; '.join(labels)}"
        elif worst_multiplier > 1.0:
            summary = f"Detections in WARNING zone (risk ×{worst_multiplier:.1f})"
        else:
            summary = "All detections within safe zones"

        annotated = self._annotate(frame, active, violations) if frame is not None else None

        return ZoneAnalysis(
            active_zones=active,
            zone_violations=violations,
            risk_multiplier=worst_multiplier,
            summary=summary,
            annotated_frame=annotated,
        )

    # ── Frame Annotation ──────────────────────────────────────────────

    def _annotate(self, frame: np.ndarray, zones: list[Zone],
                  violations: list[ZoneViolation]) -> np.ndarray:
        out = frame.copy()
        h, w = out.shape[:2]
        violation_zone_ids = {v.zone.id for v in violations}

        for zone in zones:
            x1, y1, x2, y2 = zone.bbox
            px1, py1 = int(x1 * w), int(y1 * h)
            px2, py2 = int(x2 * w), int(y2 * h)
            color = ZONE_COLORS[zone.type]

            # Semi-transparent fill
            overlay = out.copy()
            alpha = 0.18 if zone.id not in violation_zone_ids else 0.38
            cv2.rectangle(overlay, (px1, py1), (px2, py2), color, -1)
            cv2.addWeighted(overlay, alpha, out, 1 - alpha, 0, out)

            # Border — thicker if violated
            thickness = 3 if zone.id in violation_zone_ids else 1
            cv2.rectangle(out, (px1, py1), (px2, py2), color, thickness)

            # Label
            label = f"{zone.type[:3]} · {zone.name}"
            cv2.putText(out, label, (px1 + 4, py1 + 16),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1)

            # Violation flash text
            if zone.id in violation_zone_ids:
                cv2.putText(out, "⚠ VIOLATION", (px1 + 4, py2 - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        return out

    def all_zones_as_dict(self) -> list[dict]:
        return [z.to_dict() for z in self.zones]
