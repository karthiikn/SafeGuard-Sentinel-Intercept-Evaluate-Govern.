"""
SafeGuard Sentinel — Fleet Manager
Tracks multiple robot agents simultaneously.
Each robot has its own state, risk history, and decision log.
The fleet manager aggregates status for the dashboard and
enforces fleet-level safety rules (e.g., two robots can't
both be in WARNING state and both move toward the same zone).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from collections import deque
import time


# ─────────────────────────────────────────────
#  Robot State
# ─────────────────────────────────────────────

class RobotStatus(str, Enum):
    IDLE      = "IDLE"
    OPERATING = "OPERATING"
    PAUSED    = "PAUSED"
    EMERGENCY = "EMERGENCY"
    OFFLINE   = "OFFLINE"


@dataclass
class RobotState:
    agent_id:        str
    display_name:    str
    status:          RobotStatus = RobotStatus.IDLE
    last_action:     Optional[str] = None
    last_verdict:    Optional[str] = None
    last_risk_score: float = 0.0
    total_decisions: int = 0
    blocked_count:   int = 0
    warned_count:    int = 0
    allowed_count:   int = 0
    last_seen:       float = field(default_factory=time.time)
    location_hint:   Optional[str] = None      # e.g. "Zone A", "Bay 3"
    decision_log:    deque = field(default_factory=lambda: deque(maxlen=20))

    @property
    def block_rate(self) -> float:
        if self.total_decisions == 0:
            return 0.0
        return self.blocked_count / self.total_decisions

    @property
    def is_online(self) -> bool:
        return (time.time() - self.last_seen) < 30.0   # 30s timeout

    @property
    def risk_level(self) -> str:
        if self.last_risk_score >= 0.75:   return "critical"
        if self.last_risk_score >= 0.40:   return "elevated"
        return "normal"

    def record_decision(self, action_type: str, verdict: str, risk_score: float):
        self.last_action     = action_type
        self.last_verdict    = verdict
        self.last_risk_score = risk_score
        self.total_decisions += 1
        self.last_seen       = time.time()

        if verdict == "BLOCK":
            self.blocked_count += 1
            self.status = RobotStatus.PAUSED
        elif verdict == "WARN":
            self.warned_count += 1
            self.status = RobotStatus.OPERATING
        else:
            self.allowed_count += 1
            self.status = RobotStatus.OPERATING

        if action_type == "STOP":
            self.status = RobotStatus.IDLE

        self.decision_log.appendleft({
            "action":    action_type,
            "verdict":   verdict,
            "risk":      risk_score,
            "timestamp": time.time(),
        })

    def to_dict(self) -> dict:
        return {
            "agent_id":        self.agent_id,
            "display_name":    self.display_name,
            "status":          self.status,
            "last_action":     self.last_action,
            "last_verdict":    self.last_verdict,
            "last_risk_score": round(self.last_risk_score, 3),
            "total_decisions": self.total_decisions,
            "blocked_count":   self.blocked_count,
            "warned_count":    self.warned_count,
            "allowed_count":   self.allowed_count,
            "block_rate":      round(self.block_rate, 3),
            "risk_level":      self.risk_level,
            "is_online":       self.is_online,
            "location_hint":   self.location_hint,
            "last_seen":       self.last_seen,
        }


# ─────────────────────────────────────────────
#  Fleet-Level Safety Rules
# ─────────────────────────────────────────────

@dataclass
class FleetRisk:
    level:       str        # "normal" | "elevated" | "critical"
    score:       float
    description: str
    active_robots: int
    robots_in_warning: int
    robots_blocked: int


# ─────────────────────────────────────────────
#  Fleet Manager
# ─────────────────────────────────────────────

# Pre-registered robot roster (extend as needed)
DEFAULT_ROBOTS = [
    ("robot_01", "Sentinel Alpha"),
    ("robot_02", "Sentinel Beta"),
    ("robot_03", "Sentinel Gamma"),
    ("dashboard_sim", "Dashboard Sim"),
    ("robot_sim_01",  "Demo Simulator"),
]


class FleetManager:
    """
    Tracks all robot agents, records their decisions,
    and computes fleet-level risk metrics.
    """

    def __init__(self):
        self.robots: dict[str, RobotState] = {}
        # Pre-register known robots
        for agent_id, name in DEFAULT_ROBOTS:
            self._ensure_robot(agent_id, name)

    def _ensure_robot(self, agent_id: str,
                      display_name: Optional[str] = None) -> RobotState:
        if agent_id not in self.robots:
            name = display_name or f"Robot {agent_id[-4:]}"
            self.robots[agent_id] = RobotState(
                agent_id=agent_id,
                display_name=name,
            )
        return self.robots[agent_id]

    # ── Record Decision ───────────────────────────────────────────────

    def record(self, agent_id: str, action_type: str,
               verdict: str, risk_score: float,
               location_hint: Optional[str] = None):
        robot = self._ensure_robot(agent_id)
        robot.record_decision(action_type, verdict, risk_score)
        if location_hint:
            robot.location_hint = location_hint

    # ── Fleet Risk Assessment ─────────────────────────────────────────

    def fleet_risk(self) -> FleetRisk:
        online = [r for r in self.robots.values() if r.is_online]
        blocked  = [r for r in online if r.last_verdict == "BLOCK"]
        warning  = [r for r in online if r.last_verdict == "WARN"]
        critical = [r for r in online if r.last_risk_score >= 0.75]

        if len(critical) >= 2 or len(blocked) >= 2:
            level = "critical"
            score = 0.9
            desc  = (f"{len(blocked)} robot(s) blocked, {len(critical)} at critical risk. "
                     f"Fleet-wide pause recommended.")
        elif len(blocked) == 1 or len(warning) >= 2:
            level = "elevated"
            score = 0.55
            desc  = (f"{len(blocked)} blocked, {len(warning)} warned. "
                     f"Fleet operating with restrictions.")
        else:
            level = "normal"
            avg   = sum(r.last_risk_score for r in online) / max(len(online), 1)
            score = avg
            desc  = f"{len(online)} robot(s) online. Fleet operating normally."

        return FleetRisk(
            level=level,
            score=round(score, 3),
            description=desc,
            active_robots=len(online),
            robots_in_warning=len(warning),
            robots_blocked=len(blocked),
        )

    # ── Fleet-Level Safety Rule ───────────────────────────────────────

    def check_fleet_conflict(self, agent_id: str, action_type: str) -> Optional[str]:
        """
        Returns a blocking reason string if fleet-level rules prevent
        this robot from acting, or None if it's fine.
        """
        online = [r for r in self.robots.values()
                  if r.is_online and r.agent_id != agent_id]

        # Rule: If 2+ other robots are already blocked, pause all movement
        blocked_others = [r for r in online if r.last_verdict == "BLOCK"]
        if len(blocked_others) >= 2 and action_type in (
                "MOVE_FORWARD", "NAVIGATE_TO", "ARM_EXTEND", "SPEED_INCREASE"):
            names = ", ".join(r.display_name for r in blocked_others[:2])
            return (f"Fleet conflict: {names} are blocked. "
                    f"Fleet-wide movement suspended until resolved.")

        # Rule: Don't allow a 4th robot to start moving if 3 are already in WARN
        warned_others = [r for r in online if r.last_verdict == "WARN"]
        if len(warned_others) >= 3 and action_type == "MOVE_FORWARD":
            return ("Fleet saturation: 3+ robots already in WARNING state. "
                    "New movement requests denied until fleet risk normalises.")

        return None

    # ── Queries ───────────────────────────────────────────────────────

    def get_robot(self, agent_id: str) -> Optional[RobotState]:
        return self.robots.get(agent_id)

    def all_robots(self) -> list[dict]:
        return [r.to_dict() for r in self.robots.values()]

    def online_robots(self) -> list[dict]:
        return [r.to_dict() for r in self.robots.values() if r.is_online]

    def fleet_summary(self) -> dict:
        risk = self.fleet_risk()
        return {
            "fleet_risk_level": risk.level,
            "fleet_risk_score": risk.score,
            "fleet_description": risk.description,
            "active_robots": risk.active_robots,
            "robots_in_warning": risk.robots_in_warning,
            "robots_blocked": risk.robots_blocked,
            "robots": self.online_robots(),
        }
