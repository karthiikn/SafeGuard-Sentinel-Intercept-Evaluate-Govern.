"""
SafeGuard Sentinel — FastAPI Backend
The core intercept layer. Robot agents POST proposed actions here;
the system returns a SafetyDecision before anything executes.

Endpoints:
  POST /evaluate        — submit a proposed action for safety evaluation
  GET  /scene           — latest scene snapshot (vision + detections)
  GET  /history         — last N decisions
  GET  /health          — system health check
  GET  /ws              — WebSocket for real-time dashboard updates
"""

from __future__ import annotations
import asyncio
import json
import logging
import time
import uuid
from collections import deque
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from vision_module import VisionEngine, SceneSnapshot
from safety_engine import PolicyEngine, ProposedAction, ActionType, SafetyDecision
from llm_reasoner import LLMReasoner

# ─────────────────────────────────────────────
#  Configuration
# ─────────────────────────────────────────────

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("sentinel.api")

MAX_HISTORY = 100
SCENE_REFRESH_INTERVAL = 0.5   # seconds between background scene captures

# ─────────────────────────────────────────────
#  Global State
# ─────────────────────────────────────────────

vision:  VisionEngine
policy:  PolicyEngine
reasoner: LLMReasoner

decision_history: deque[dict] = deque(maxlen=MAX_HISTORY)
latest_scene:     Optional[SceneSnapshot] = None
ws_clients:       list[WebSocket] = []


# ─────────────────────────────────────────────
#  Startup / Shutdown
# ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global vision, policy, reasoner
    logger.info("🚀 SafeGuard Sentinel starting…")
    vision   = VisionEngine(force_simulation=False)   # auto-detects camera
    policy   = PolicyEngine()
    reasoner = LLMReasoner()                          # uses ANTHROPIC_API_KEY if set
    # Background scene refresh loop
    task = asyncio.create_task(_scene_refresh_loop())
    yield
    task.cancel()
    vision.release()
    logger.info("🛑 SafeGuard Sentinel stopped.")


app = FastAPI(
    title="SafeGuard Sentinel",
    description="AI Governance Layer for Autonomous Robotics",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
#  Background Tasks
# ─────────────────────────────────────────────

async def _scene_refresh_loop():
    """Continuously captures scene frames and pushes to WebSocket clients."""
    global latest_scene
    while True:
        try:
            latest_scene = await asyncio.get_event_loop().run_in_executor(
                None, vision.capture)
            await _broadcast_scene(latest_scene)
        except Exception as e:
            logger.warning(f"Scene refresh error: {e}")
        await asyncio.sleep(SCENE_REFRESH_INTERVAL)


async def _broadcast_scene(scene: SceneSnapshot):
    payload = json.dumps({
        "type": "scene_update",
        "human_count": scene.human_count,
        "obstacle_count": scene.obstacle_count,
        "nearest_human": scene.nearest_human_distance,
        "detections": [
            {
                "label": d.label,
                "confidence": round(d.confidence, 3),
                "distance": d.distance_estimate,
                "is_human": d.is_human,
            }
            for d in scene.detections
        ],
        "frame": scene.frame_base64,
        "timestamp": scene.timestamp,
    })
    dead = []
    for ws in ws_clients:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        ws_clients.remove(ws)


async def _broadcast_decision(decision_dict: dict):
    payload = json.dumps({"type": "decision", **decision_dict})
    dead = []
    for ws in ws_clients:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        ws_clients.remove(ws)


# ─────────────────────────────────────────────
#  Request / Response Models
# ─────────────────────────────────────────────

class ActionRequest(BaseModel):
    action_type: str = Field(..., example="MOVE_FORWARD")
    parameters: dict  = Field(default_factory=dict, example={"speed": 1.2})
    agent_id: str     = Field(default="robot_01")
    request_id: Optional[str] = None


class DecisionResponse(BaseModel):
    request_id:   str
    verdict:      str
    risk_score:   float
    reasoning:    str
    llm_explanation: Optional[str]
    violations:   list[dict]
    recommended_alternative: Optional[str]
    scene_summary: dict
    timestamp:    float


# ─────────────────────────────────────────────
#  Routes
# ─────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "online",
        "vision_mode": "simulation" if vision.simulation else "live",
        "llm_enabled": reasoner.enabled,
        "decisions_logged": len(decision_history),
        "timestamp": time.time(),
    }


@app.post("/evaluate", response_model=DecisionResponse)
async def evaluate_action(req: ActionRequest):
    """
    Main intercept endpoint.
    Submit a proposed robot action; receive ALLOW / WARN / BLOCK verdict.
    """
    request_id = req.request_id or str(uuid.uuid4())[:8]
    logger.info(f"[{request_id}] Evaluating: {req.action_type} params={req.parameters}")

    # 1. Capture scene
    scene = latest_scene or await asyncio.get_event_loop().run_in_executor(
        None, vision.capture)

    # 2. Build action object
    try:
        action_type = ActionType(req.action_type)
    except ValueError:
        action_type = ActionType.CUSTOM

    proposed = ProposedAction(
        action_type=action_type,
        parameters=req.parameters,
        agent_id=req.agent_id,
        request_id=request_id,
    )

    # 3. Policy evaluation
    decision: SafetyDecision = policy.evaluate(proposed, scene)

    # 4. LLM explanation (non-blocking)
    llm_explanation = await asyncio.get_event_loop().run_in_executor(
        None, reasoner.explain, decision)

    # 5. Build response dict
    resp_dict = {
        "request_id":            request_id,
        "verdict":               decision.verdict,
        "risk_score":            decision.risk_score,
        "reasoning":             decision.reasoning,
        "llm_explanation":       llm_explanation,
        "violations":            [
            {"rule_id": v.rule_id, "severity": v.severity, "description": v.description}
            for v in decision.violations
        ],
        "recommended_alternative": decision.recommended_alternative,
        "scene_summary":         decision.snapshot_summary or {},
        "timestamp":             decision.timestamp,
    }

    # 6. Store + broadcast
    decision_history.appendleft(resp_dict)
    await _broadcast_decision(resp_dict)

    logger.info(f"[{request_id}] Verdict: {decision.verdict} | Risk: {decision.risk_score:.2f}")
    return resp_dict


@app.get("/scene")
async def get_scene():
    """Returns the latest scene snapshot (without frame data for speed)."""
    if not latest_scene:
        return {"error": "No scene captured yet"}
    return {
        "human_count":    latest_scene.human_count,
        "obstacle_count": latest_scene.obstacle_count,
        "nearest_human":  latest_scene.nearest_human_distance,
        "detection_count": len(latest_scene.detections),
        "detections": [
            {"label": d.label, "confidence": round(d.confidence, 3),
             "distance": d.distance_estimate, "is_human": d.is_human}
            for d in latest_scene.detections
        ],
        "timestamp": latest_scene.timestamp,
    }


@app.get("/history")
async def get_history(limit: int = 20):
    """Returns the last N safety decisions."""
    items = list(decision_history)[:limit]
    # strip frame data to keep response lean
    for item in items:
        item.pop("frame", None)
    return {"decisions": items, "total": len(decision_history)}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    ws_clients.append(websocket)
    logger.info(f"WebSocket connected. Total clients: {len(ws_clients)}")
    try:
        while True:
            # Keep connection alive; actual data is pushed by background loop
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_clients.remove(websocket)
        logger.info(f"WebSocket disconnected. Total clients: {len(ws_clients)}")


# ─────────────────────────────────────────────
#  Run directly for development
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)
