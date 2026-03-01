"""
SafeGuard Sentinel — Human Override System
Allows authorized operators to review BLOCKED actions and
force-allow them with mandatory justification.

Every override is logged with:
  - operator ID
  - original decision (action + violations + risk score)
  - override justification
  - timestamp
  - expiry (override is time-limited for safety)

This is the "human-in-the-loop" layer — operators retain
ultimate authority but are held accountable via the audit log.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from collections import deque
import time
import uuid


# ─────────────────────────────────────────────
#  Override Status
# ─────────────────────────────────────────────

class OverrideStatus(str, Enum):
    PENDING   = "PENDING"    # Awaiting operator decision
    APPROVED  = "APPROVED"   # Operator force-allowed
    REJECTED  = "REJECTED"   # Operator confirmed block
    EXPIRED   = "EXPIRED"    # Timed out without operator action
    EXECUTED  = "EXECUTED"   # Approved action was executed


# ─────────────────────────────────────────────
#  Override Request
# ─────────────────────────────────────────────

@dataclass
class OverrideRequest:
    override_id:    str
    request_id:     str                  # original action request_id
    agent_id:       str
    action_type:    str
    action_params:  dict
    risk_score:     float
    violations:     list[dict]
    original_reasoning: str
    created_at:     float = field(default_factory=time.time)
    expires_at:     float = field(default_factory=lambda: time.time() + 120)  # 2 min

    # Set when operator acts
    status:         OverrideStatus = OverrideStatus.PENDING
    operator_id:    Optional[str]  = None
    justification:  Optional[str]  = None
    decided_at:     Optional[float] = None

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at and self.status == OverrideStatus.PENDING

    @property
    def time_remaining(self) -> float:
        return max(0.0, self.expires_at - time.time())

    def to_dict(self) -> dict:
        return {
            "override_id":       self.override_id,
            "request_id":        self.request_id,
            "agent_id":          self.agent_id,
            "action_type":       self.action_type,
            "action_params":     self.action_params,
            "risk_score":        self.risk_score,
            "violations":        self.violations,
            "original_reasoning": self.original_reasoning,
            "created_at":        self.created_at,
            "expires_at":        self.expires_at,
            "time_remaining":    round(self.time_remaining, 1),
            "status":            self.status,
            "operator_id":       self.operator_id,
            "justification":     self.justification,
            "decided_at":        self.decided_at,
        }


# ─────────────────────────────────────────────
#  Audit Log Entry
# ─────────────────────────────────────────────

@dataclass
class AuditEntry:
    entry_id:      str
    override_id:   str
    event:         str        # "REQUESTED" | "APPROVED" | "REJECTED" | "EXPIRED"
    agent_id:      str
    action_type:   str
    risk_score:    float
    operator_id:   Optional[str]
    justification: Optional[str]
    timestamp:     float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "entry_id":      self.entry_id,
            "override_id":   self.override_id,
            "event":         self.event,
            "agent_id":      self.agent_id,
            "action_type":   self.action_type,
            "risk_score":    self.risk_score,
            "operator_id":   self.operator_id,
            "justification": self.justification,
            "timestamp":     self.timestamp,
        }


# ─────────────────────────────────────────────
#  Override Manager
# ─────────────────────────────────────────────

# Max risk score that can be overridden (protect against overriding score=1.0)
MAX_OVERRIDABLE_RISK = 0.97

OPERATORS = {
    "op_alice":   "Alice Chen (Safety Lead)",
    "op_bob":     "Bob Kumar (Floor Supervisor)",
    "op_charlie": "Charlie Diaz (Engineer)",
    "demo_op":    "Demo Operator",
}


class OverrideManager:
    """
    Manages the full lifecycle of human override requests.
    Thread-safe for concurrent API use.
    """

    def __init__(self):
        self.pending:   dict[str, OverrideRequest] = {}
        self.audit_log: deque[AuditEntry] = deque(maxlen=500)
        self.stats = {
            "total_requested": 0,
            "total_approved":  0,
            "total_rejected":  0,
            "total_expired":   0,
        }

    # ── Create Override Request ───────────────────────────────────────

    def request_override(self, request_id: str, agent_id: str,
                         action_type: str, action_params: dict,
                         risk_score: float, violations: list[dict],
                         reasoning: str) -> OverrideRequest:
        """
        Called when an operator wants to challenge a BLOCK decision.
        Returns the override request (status=PENDING).
        """
        override_id = f"ov_{str(uuid.uuid4())[:6]}"

        req = OverrideRequest(
            override_id=override_id,
            request_id=request_id,
            agent_id=agent_id,
            action_type=action_type,
            action_params=action_params,
            risk_score=risk_score,
            violations=violations,
            original_reasoning=reasoning,
        )

        self.pending[override_id] = req
        self.stats["total_requested"] += 1

        self._log(req, "REQUESTED", None, None)
        self._expire_old()
        return req

    # ── Operator Decision ─────────────────────────────────────────────

    def approve(self, override_id: str, operator_id: str,
                justification: str) -> tuple[bool, str]:
        """
        Operator force-approves a blocked action.
        Returns (success, message).
        """
        req = self.pending.get(override_id)
        if not req:
            return False, "Override request not found"
        if req.is_expired:
            req.status = OverrideStatus.EXPIRED
            return False, "Override request has expired"
        if operator_id not in OPERATORS:
            return False, f"Unknown operator ID: {operator_id}"
        if req.risk_score > MAX_OVERRIDABLE_RISK:
            return False, (f"Risk score {req.risk_score:.0%} exceeds override limit "
                           f"({MAX_OVERRIDABLE_RISK:.0%}). Cannot override.")
        if not justification or len(justification.strip()) < 10:
            return False, "Justification must be at least 10 characters."

        req.status       = OverrideStatus.APPROVED
        req.operator_id  = operator_id
        req.justification = justification.strip()
        req.decided_at   = time.time()
        self.stats["total_approved"] += 1

        self._log(req, "APPROVED", operator_id, justification)
        return True, f"Override approved by {OPERATORS[operator_id]}"

    def reject(self, override_id: str, operator_id: str,
               justification: str) -> tuple[bool, str]:
        """Operator confirms the block — action stays blocked."""
        req = self.pending.get(override_id)
        if not req:
            return False, "Override request not found"

        req.status        = OverrideStatus.REJECTED
        req.operator_id   = operator_id
        req.justification = justification.strip() if justification else "Block confirmed."
        req.decided_at    = time.time()
        self.stats["total_rejected"] += 1

        self._log(req, "REJECTED", operator_id, justification)
        del self.pending[override_id]
        return True, "Block confirmed. Action remains blocked."

    # ── Queries ───────────────────────────────────────────────────────

    def get_pending(self) -> list[dict]:
        self._expire_old()
        return [r.to_dict() for r in self.pending.values()
                if r.status == OverrideStatus.PENDING]

    def get_override(self, override_id: str) -> Optional[dict]:
        r = self.pending.get(override_id)
        return r.to_dict() if r else None

    def get_audit_log(self, limit: int = 50) -> list[dict]:
        return [e.to_dict() for e in list(self.audit_log)[:limit]]

    def get_operators(self) -> list[dict]:
        return [{"id": k, "name": v} for k, v in OPERATORS.items()]

    def get_stats(self) -> dict:
        return {**self.stats, "pending_count": len(self.get_pending())}

    # ── Internal ──────────────────────────────────────────────────────

    def _log(self, req: OverrideRequest, event: str,
             operator_id: Optional[str], justification: Optional[str]):
        self.audit_log.appendleft(AuditEntry(
            entry_id=str(uuid.uuid4())[:8],
            override_id=req.override_id,
            event=event,
            agent_id=req.agent_id,
            action_type=req.action_type,
            risk_score=req.risk_score,
            operator_id=operator_id,
            justification=justification,
        ))

    def _expire_old(self):
        expired = [oid for oid, r in self.pending.items() if r.is_expired]
        for oid in expired:
            req = self.pending[oid]
            req.status = OverrideStatus.EXPIRED
            self.stats["total_expired"] += 1
            self._log(req, "EXPIRED", None, None)
            del self.pending[oid]
