"""
SafeGuard Sentinel — LLM Reasoning Layer
Uses Claude claude-sonnet-4-6 to generate human-readable explanations
for safety decisions. Optional; system works without it.
"""

from __future__ import annotations
import os
import json
import time
import logging
from typing import Optional

from safety_engine import SafetyDecision, Verdict

logger = logging.getLogger(__name__)

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("anthropic SDK not installed — LLM explanations disabled")


# ─────────────────────────────────────────────
#  System Prompt
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """You are SafeGuard Sentinel's AI conscience — an expert robotic safety officer.
Your job is to explain safety decisions made about autonomous robot actions in clear, 
authoritative language that non-technical operators can understand.

Guidelines:
- Be concise (2-4 sentences max)
- Lead with the verdict and risk level
- Explain WHY this specific action is or isn't safe in this specific environment
- If blocked, briefly describe what the robot should do instead
- Use professional but accessible language (no jargon)
- Never be alarmist — be calm and clear
- Format: plain text, no markdown, no lists"""


# ─────────────────────────────────────────────
#  Reasoner Class
# ─────────────────────────────────────────────

class LLMReasoner:
    """
    Wraps Claude API to produce natural language explanations.
    Falls back to rule-generated reasoning if API unavailable.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.enabled = ANTHROPIC_AVAILABLE
        self.client = None
        self._cache: dict[str, tuple[str, float]] = {}  # cache_key → (text, timestamp)
        self.cache_ttl = 30.0  # seconds

        if self.enabled:
            key = api_key or os.getenv("ANTHROPIC_API_KEY")
            if not key:
                logger.warning("ANTHROPIC_API_KEY not set — LLM explanations disabled")
                self.enabled = False
            else:
                self.client = anthropic.Anthropic(api_key=key)

    def explain(self, decision: SafetyDecision) -> str:
        """
        Returns a human-readable explanation of the safety decision.
        Uses LLM if available, otherwise returns rule-generated reasoning.
        """
        if not self.enabled:
            return self._fallback_explanation(decision)

        cache_key = self._cache_key(decision)
        cached = self._cache.get(cache_key)
        if cached and (time.time() - cached[1]) < self.cache_ttl:
            return cached[0]

        try:
            prompt = self._build_prompt(decision)
            response = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=200,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            self._cache[cache_key] = (text, time.time())
            return text
        except Exception as e:
            logger.warning(f"LLM call failed ({e}) — using fallback explanation")
            return self._fallback_explanation(decision)

    # ──────────────────────────────────────────────────────────────────

    def _build_prompt(self, decision: SafetyDecision) -> str:
        action = decision.action
        snap = decision.snapshot_summary or {}
        violations_text = ""
        if decision.violations:
            violations_text = "\n".join(
                f"- [{v.severity}] {v.rule_id}: {v.description}"
                for v in decision.violations
            )
        else:
            violations_text = "None"

        return f"""Safety evaluation result for autonomous robot action:

ACTION: {action.action_type if action else "Unknown"}
PARAMETERS: {json.dumps(action.parameters if action else {}, indent=2)}
VERDICT: {decision.verdict}
RISK SCORE: {decision.risk_score:.2f} / 1.00

ENVIRONMENT:
- Humans detected: {snap.get('human_count', 0)}
- Obstacles detected: {snap.get('obstacle_count', 0)}
- Nearest human distance: {snap.get('nearest_human', 'None')}

POLICY VIOLATIONS:
{violations_text}

RECOMMENDED ALTERNATIVE: {decision.recommended_alternative or 'None'}

Please explain this safety decision to a non-technical robot operator in 2-4 sentences."""

    def _fallback_explanation(self, decision: SafetyDecision) -> str:
        """Simple template-based fallback explanation."""
        snap = decision.snapshot_summary or {}
        action_name = decision.action.action_type if decision.action else "action"
        humans = snap.get("human_count", 0)
        nearest = snap.get("nearest_human", None)

        if decision.verdict == Verdict.ALLOW:
            return (
                f"The proposed {action_name} has been approved. "
                f"The environment appears clear with {humans} human(s) detected at safe distance. "
                f"Risk score is low at {decision.risk_score:.0%}."
            )
        elif decision.verdict == Verdict.WARN:
            return (
                f"The {action_name} is proceeding with caution. "
                f"Warning: {humans} human(s) detected{f' at {nearest} range' if nearest else ''}. "
                f"Risk score: {decision.risk_score:.0%}. Operator monitoring recommended."
            )
        else:  # BLOCK
            main_violation = decision.violations[0].description if decision.violations else "Safety policy violation"
            alt = decision.recommended_alternative or "Halt and await operator instruction"
            return (
                f"ACTION BLOCKED. {main_violation} "
                f"Risk score: {decision.risk_score:.0%}. "
                f"Recommended: {alt}."
            )

    def _cache_key(self, decision: SafetyDecision) -> str:
        action = decision.action
        snap = decision.snapshot_summary or {}
        return (
            f"{action.action_type if action else 'none'}_"
            f"{decision.verdict}_"
            f"{snap.get('human_count', 0)}_"
            f"{snap.get('nearest_human', 'none')}_"
            f"{decision.risk_score:.2f}"
        )
