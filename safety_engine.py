"""
SafeGuard Sentinel — Safety Policy Engine
Evaluates proposed robot actions against scene context and returns
a structured SafetyDecision (ALLOW / BLOCK / WARN).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import time

from vision_module import SceneSnapshot


# ─────────────────────────────────────────────
#  Action & Decision Types
# ─────────────────────────────────────────────

class ActionType(str, Enum):
    MOVE_FORWARD   = "MOVE_FORWARD"
    MOVE_BACKWARD  = "MOVE_BACKWARD"
    ROTATE         = "ROTATE"
    GRIPPER_CLOSE  = "GRIPPER_CLOSE"
    GRIPPER_OPEN   = "GRIPPER_OPEN"
    SPEED_INCREASE = "SPEED_INCREASE"
    STOP           = "STOP"
    ARM_EXTEND     = "ARM_EXTEND"
    NAVIGATE_TO    = "NAVIGATE_TO"
    CUSTOM         = "CUSTOM"


class Verdict(str, Enum):
    ALLOW = "ALLOW"
    WARN  = "WARN"
    BLOCK = "BLOCK"


@dataclass
class ProposedAction:
    action_type: ActionType
    parameters: dict = field(default_factory=dict)
    # e.g. {"speed": 1.5, "direction": "north", "distance_m": 2.0}
    agent_id: str = "robot_01"
    request_id: Optional[str] = None


@dataclass
class PolicyViolation:
    rule_id: str
    severity: str          # "critical" | "warning"
    description: str


@dataclass
class SafetyDecision:
    verdict: Verdict
    risk_score: float               # 0.0 (safe) → 1.0 (critical)
    violations: list[PolicyViolation]
    reasoning: str
    recommended_alternative: Optional[str]
    timestamp: float = field(default_factory=time.time)
    action: Optional[ProposedAction] = None
    snapshot_summary: Optional[dict] = None


# ─────────────────────────────────────────────
#  Policy Rules
# ─────────────────────────────────────────────

class PolicyEngine:
    """
    Stateless rule evaluator.
    Rules are evaluated in priority order; a BLOCK from any critical
    rule immediately ends evaluation with a BLOCK verdict.
    """

    def evaluate(self, action: ProposedAction,
                 scene: SceneSnapshot) -> SafetyDecision:

        violations: list[PolicyViolation] = []
        risk_score = 0.0

        # ── Run all rules ──────────────────────────────────────────────
        risk_score, violations = self._run_rules(action, scene)

        # ── Determine verdict ──────────────────────────────────────────
        critical_violations = [v for v in violations if v.severity == "critical"]
        warning_violations  = [v for v in violations if v.severity == "warning"]

        if critical_violations or risk_score >= 0.75:
            verdict = Verdict.BLOCK
        elif warning_violations or risk_score >= 0.40:
            verdict = Verdict.WARN
        else:
            verdict = Verdict.ALLOW

        reasoning = self._build_reasoning(action, scene, violations, risk_score, verdict)
        alternative = self._suggest_alternative(action, verdict, scene)

        return SafetyDecision(
            verdict=verdict,
            risk_score=round(risk_score, 3),
            violations=violations,
            reasoning=reasoning,
            recommended_alternative=alternative,
            action=action,
            snapshot_summary={
                "human_count": scene.human_count,
                "obstacle_count": scene.obstacle_count,
                "nearest_human": scene.nearest_human_distance,
                "total_detections": len(scene.detections),
            },
        )

    # ──────────────────────────────────────────────────────────────────
    #  Rule Implementations
    # ──────────────────────────────────────────────────────────────────

    def _run_rules(self, action: ProposedAction,
                   scene: SceneSnapshot) -> tuple[float, list[PolicyViolation]]:
        violations: list[PolicyViolation] = []
        score = 0.0

        # RULE 1: Human proximity + movement actions
        if scene.human_count > 0:
            near_human = scene.nearest_human_distance == "near"
            mid_human  = scene.nearest_human_distance == "mid"

            if action.action_type in (ActionType.MOVE_FORWARD,
                                      ActionType.NAVIGATE_TO,
                                      ActionType.ARM_EXTEND):
                if near_human:
                    violations.append(PolicyViolation(
                        rule_id="HUMAN_PROXIMITY_CRITICAL",
                        severity="critical",
                        description=(
                            f"Human detected at NEAR range. "
                            f"Action '{action.action_type}' poses imminent collision risk."
                        ),
                    ))
                    score = max(score, 0.95)
                elif mid_human:
                    violations.append(PolicyViolation(
                        rule_id="HUMAN_PROXIMITY_WARNING",
                        severity="warning",
                        description=(
                            f"Human detected at MID range. "
                            f"Action '{action.action_type}' requires reduced speed."
                        ),
                    ))
                    score = max(score, 0.55)

        # RULE 2: Multiple humans present during any motion
        if scene.human_count >= 2 and action.action_type not in (
                ActionType.STOP, ActionType.GRIPPER_OPEN):
            violations.append(PolicyViolation(
                rule_id="CROWDED_SCENE",
                severity="warning",
                description=f"{scene.human_count} humans detected — crowded environment.",
            ))
            score = max(score, 0.45)

        # RULE 3: High speed in occupied space
        speed = action.parameters.get("speed", 1.0)
        if speed > 1.5 and scene.human_count > 0:
            violations.append(PolicyViolation(
                rule_id="EXCESSIVE_SPEED_HUMAN_PRESENT",
                severity="critical",
                description=(
                    f"Requested speed {speed}m/s exceeds 1.5m/s limit "
                    f"while {scene.human_count} human(s) present."
                ),
            ))
            score = max(score, 0.85)
        elif speed > 2.5:
            violations.append(PolicyViolation(
                rule_id="EXCESSIVE_SPEED",
                severity="warning",
                description=f"Speed {speed}m/s exceeds absolute 2.5m/s threshold.",
            ))
            score = max(score, 0.50)

        # RULE 4: Gripper close when human is near
        if action.action_type == ActionType.GRIPPER_CLOSE:
            if scene.nearest_human_distance == "near":
                violations.append(PolicyViolation(
                    rule_id="GRIPPER_HUMAN_NEAR",
                    severity="critical",
                    description="Gripper actuation blocked: human within near range.",
                ))
                score = max(score, 0.90)

        # RULE 5: Arm extend when scene not clear
        if action.action_type == ActionType.ARM_EXTEND:
            if scene.human_count > 0 or scene.obstacle_count > 2:
                violations.append(PolicyViolation(
                    rule_id="ARM_EXTEND_OBSTRUCTED",
                    severity="warning" if scene.human_count == 0 else "critical",
                    description=(
                        f"Arm extension risky: {scene.human_count} human(s), "
                        f"{scene.obstacle_count} obstacle(s) in scene."
                    ),
                ))
                score = max(score, 0.80 if scene.human_count > 0 else 0.45)

        # RULE 6: Speed increase while any obstacle/human present
        if action.action_type == ActionType.SPEED_INCREASE:
            if scene.human_count > 0 or scene.obstacle_count > 0:
                violations.append(PolicyViolation(
                    rule_id="SPEED_INCREASE_BLOCKED",
                    severity="critical" if scene.human_count > 0 else "warning",
                    description="Speed increase denied — scene is not clear.",
                ))
                score = max(score, 0.80 if scene.human_count > 0 else 0.50)

        # RULE 7: STOP is always safe — override everything
        if action.action_type == ActionType.STOP:
            violations.clear()
            score = 0.0

        # RULE 8: Baseline scene risk (minor penalty for clutter)
        if scene.obstacle_count > 0 and not violations:
            score = max(score, min(scene.obstacle_count * 0.06, 0.25))

        return score, violations

    # ──────────────────────────────────────────────────────────────────
    #  Reasoning & Alternative Generation
    # ──────────────────────────────────────────────────────────────────

    def _build_reasoning(self, action: ProposedAction, scene: SceneSnapshot,
                         violations: list[PolicyViolation],
                         score: float, verdict: Verdict) -> str:
        lines = [
            f"Action '{action.action_type}' evaluated with risk score {score:.2f}.",
            f"Scene: {scene.human_count} human(s), {scene.obstacle_count} obstacle(s).",
        ]
        if scene.nearest_human_distance:
            lines.append(f"Nearest human: {scene.nearest_human_distance} range.")
        if violations:
            lines.append("Policy violations:")
            for v in violations:
                lines.append(f"  [{v.severity.upper()}] {v.rule_id}: {v.description}")
        if verdict == Verdict.ALLOW:
            lines.append("✅ No policy violations. Action approved for execution.")
        elif verdict == Verdict.WARN:
            lines.append("⚠️ Warnings present. Proceeding with reduced authority.")
        else:
            lines.append("🛑 Critical violations detected. Action is BLOCKED.")
        return " | ".join(lines)

    def _suggest_alternative(self, action: ProposedAction,
                             verdict: Verdict,
                             scene: SceneSnapshot) -> Optional[str]:
        if verdict == Verdict.ALLOW:
            return None
        suggestions = {
            ActionType.MOVE_FORWARD:   "STOP and wait for humans to clear the path",
            ActionType.NAVIGATE_TO:    "Recalculate route avoiding occupied zones",
            ActionType.ARM_EXTEND:     "Wait until scene is clear, then re-attempt",
            ActionType.GRIPPER_CLOSE:  "Move arm to a safe position away from humans",
            ActionType.SPEED_INCREASE: "Maintain current speed until area is clear",
            ActionType.SPEED_INCREASE: "Reduce speed to under 1.5m/s",
        }
        return suggestions.get(action.action_type,
                               "Halt current action and request human operator review")
