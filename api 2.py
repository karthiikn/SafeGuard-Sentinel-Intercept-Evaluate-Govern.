"""
SafeGuard Sentinel — FastAPI Backend (v2)
Full integration: Vision + Zones + Safety + Fleet + Override + LLM

Endpoints:
  POST /evaluate              — submit action (zone-aware + fleet-aware)
  GET  /scene                 — latest scene snapshot
  GET  /history               — decision history
  GET  /health                — system health

  GET  /zones                 — list all zones
  POST /zones                 — add a zone
  DELETE /zones/{zone_id}     — remove a zone
  POST /zones/{zone_id}/toggle — enable/disable a zone
  POST /zones/reset           — reset to defaults

  GET  /fleet                 — fleet summary
  GET  /fleet/robots          — all robot states
  GET  /fleet/{agent_id}      — single robot state

  GET  /overrides/pending     — pending override requests
  POST /overrides/request     — request override for a blocked action
  POST /overrides/{id}/approve — operator approves override
  POST /overrides/{id}/reject  — operator confirms block
  GET  /overrides/audit       — full audit log
  GET  /overrides/operators   — list of valid operator IDs
  GET  /overrides/stats       — override statistics

  WS   /ws                    — real-time dashboard WebSocket
"""

from __future__ import annotations
import asyncio
import json
import logging
import time
import uuid
from collections import deque
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from vision_module    import VisionEngine, SceneSnapshot
from safety_engine    import PolicyEngine, ProposedAction, ActionType, SafetyDecision
from llm_reasoner     import LLMReasoner
from zone_manager     import ZoneManager, ZoneType
from fleet_manager    import FleetManager
from override_manager import OverrideManager

# ─────────────────────────────────────────────
#  Config
# ─────────────────────────────────────────────

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("sentinel.api")

MAX_HISTORY            = 200
SCENE_REFRESH_INTERVAL = 0.5

# ─────────────────────────────────────────────
#  Global State
# ─────────────────────────────────────────────

vision:    VisionEngine
policy:    PolicyEngine
reasoner:  LLMReasoner
zones:     ZoneManager
fleet:     FleetManager
overrides: OverrideManager

decision_history: deque[dict] = deque(maxlen=MAX_HISTORY)
latest_scene:     Optional[SceneSnapshot] = None
ws_clients:       list[WebSocket] = []


# ─────────────────────────────────────────────
#  Startup / Shutdown
# ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global vision, policy, reasoner, zones, fleet, overrides
    logger.info("SafeGuard Sentinel v2 starting...")
    vision    = VisionEngine(force_simulation=False)
    policy    = PolicyEngine()
    reasoner  = LLMReasoner()
    zones     = ZoneManager()
    fleet     = FleetManager()
    overrides = OverrideManager()
    task = asyncio.create_task(_scene_refresh_loop())
    yield
    task.cancel()
    vision.release()
    logger.info("SafeGuard Sentinel stopped.")


app = FastAPI(
    title="SafeGuard Sentinel",
    description="AI Governance Layer for Autonomous Robotics — v2",
    version="2.0.0",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])


# ─────────────────────────────────────────────
#  Background Tasks
# ─────────────────────────────────────────────

async def _scene_refresh_loop():
    global latest_scene
    while True:
        try:
            latest_scene = await asyncio.get_event_loop().run_in_executor(
                None, vision.capture)
            await _broadcast_scene(latest_scene)
        except Exception as e:
            logger.warning(f"Scene refresh error: {e}")
        await asyncio.sleep(SCENE_REFRESH_INTERVAL)


async def _broadcast(payload: dict):
    text = json.dumps(payload)
    dead = []
    for ws in ws_clients:
        try:
            await ws.send_text(text)
        except Exception:
            dead.append(ws)
    for ws in dead:
        ws_clients.remove(ws)


async def _broadcast_scene(scene: SceneSnapshot):
    zone_analysis = zones.analyze(scene.detections)
    await _broadcast({
        "type":            "scene_update",
        "human_count":     scene.human_count,
        "obstacle_count":  scene.obstacle_count,
        "nearest_human":   scene.nearest_human_distance,
        "detections": [
            {"label": d.label, "confidence": round(d.confidence, 3),
             "distance": d.distance_estimate, "is_human": d.is_human,
             "bbox": list(d.bbox)}
            for d in scene.detections
        ],
        "zone_violations": len(zone_analysis.zone_violations),
        "zone_summary":    zone_analysis.summary,
        "active_zones":    [z.to_dict() for z in zone_analysis.active_zones],
        "frame":           scene.frame_base64,
        "timestamp":       scene.timestamp,
    })


# ─────────────────────────────────────────────
#  Pydantic Models
# ─────────────────────────────────────────────

class ActionRequest(BaseModel):
    action_type: str  = Field(..., example="MOVE_FORWARD")
    parameters:  dict = Field(default_factory=dict)
    agent_id:    str  = Field(default="robot_01")
    request_id:  Optional[str] = None


class ZoneCreateRequest(BaseModel):
    name:      str   = Field(..., example="Danger Zone A")
    zone_type: str   = Field(..., example="RESTRICTED")
    x1: float = Field(..., ge=0, le=1)
    y1: float = Field(..., ge=0, le=1)
    x2: float = Field(..., ge=0, le=1)
    y2: float = Field(..., ge=0, le=1)


class OverrideRequestBody(BaseModel):
    request_id:    str
    agent_id:      str
    action_type:   str
    action_params: dict  = Field(default_factory=dict)
    risk_score:    float
    violations:    list  = Field(default_factory=list)
    reasoning:     str   = ""


class OverrideDecisionBody(BaseModel):
    operator_id:   str = Field(..., example="op_alice")
    justification: str = Field(..., example="Operator verified area is clear")


# ─────────────────────────────────────────────
#  Core Endpoints
# ─────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status":            "online",
        "vision_mode":       "simulation" if vision.simulation else "live",
        "llm_enabled":       reasoner.enabled,
        "decisions_logged":  len(decision_history),
        "active_zones":      len(zones.get_active_zones()),
        "online_robots":     len(fleet.online_robots()),
        "pending_overrides": len(overrides.get_pending()),
        "timestamp":         time.time(),
    }


@app.post("/evaluate")
async def evaluate_action(req: ActionRequest):
    """Main intercept endpoint — zone-aware and fleet-aware."""
    request_id = req.request_id or str(uuid.uuid4())[:8]
    logger.info(f"[{request_id}] {req.agent_id} -> {req.action_type}")

    # 1. Scene
    scene = latest_scene or await asyncio.get_event_loop().run_in_executor(
        None, vision.capture)

    # 2. Zone analysis
    zone_analysis = await asyncio.get_event_loop().run_in_executor(
        None, lambda: zones.analyze(scene.detections, None))

    # 3. Fleet conflict check
    fleet_block = fleet.check_fleet_conflict(req.agent_id, req.action_type)

    # 4. Build proposed action
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

    # 5. Policy evaluation
    decision: SafetyDecision = policy.evaluate(proposed, scene)

    # 6. Apply zone risk multiplier
    adjusted_risk = min(decision.risk_score * zone_analysis.risk_multiplier, 1.0)

    # 7. Fleet override
    final_verdict = decision.verdict
    final_risk    = adjusted_risk
    fleet_note    = None
    if fleet_block:
        final_verdict = "BLOCK"
        final_risk    = max(adjusted_risk, 0.80)
        fleet_note    = fleet_block

    # 8. LLM explanation (non-blocking)
    llm_explanation = await asyncio.get_event_loop().run_in_executor(
        None, reasoner.explain, decision)

    # 9. Record in fleet
    fleet.record(req.agent_id, req.action_type, final_verdict, final_risk)

    # 10. Response
    resp = {
        "request_id":          request_id,
        "verdict":             final_verdict,
        "risk_score":          round(final_risk, 3),
        "base_risk_score":     decision.risk_score,
        "reasoning":           decision.reasoning,
        "llm_explanation":     llm_explanation,
        "violations": [
            {"rule_id": v.rule_id, "severity": v.severity, "description": v.description}
            for v in decision.violations
        ],
        "recommended_alternative": decision.recommended_alternative,
        "scene_summary":       decision.snapshot_summary or {},
        "zone_summary":        zone_analysis.summary,
        "zone_violations":     len(zone_analysis.zone_violations),
        "zone_risk_multiplier": zone_analysis.risk_multiplier,
        "fleet_note":          fleet_note,
        "fleet_summary":       fleet.fleet_summary(),
        "timestamp":           decision.timestamp,
        "action": {
            "action_type": req.action_type,
            "parameters":  req.parameters,
            "agent_id":    req.agent_id,
        },
    }

    decision_history.appendleft(resp)
    await _broadcast({"type": "decision", **resp})
    logger.info(f"[{request_id}] -> {final_verdict} (risk={final_risk:.2f})")
    return resp


@app.get("/scene")
async def get_scene():
    if not latest_scene:
        return {"error": "No scene captured yet"}
    zone_analysis = zones.analyze(latest_scene.detections)
    return {
        "human_count":     latest_scene.human_count,
        "obstacle_count":  latest_scene.obstacle_count,
        "nearest_human":   latest_scene.nearest_human_distance,
        "detections": [
            {"label": d.label, "confidence": round(d.confidence, 3),
             "distance": d.distance_estimate, "is_human": d.is_human}
            for d in latest_scene.detections
        ],
        "zone_summary":    zone_analysis.summary,
        "zone_violations": len(zone_analysis.zone_violations),
        "active_zones":    [z.to_dict() for z in zone_analysis.active_zones],
        "timestamp":       latest_scene.timestamp,
    }


@app.get("/history")
async def get_history(limit: int = 20):
    items = list(decision_history)[:limit]
    for item in items:
        item.pop("frame", None)
    return {"decisions": items, "total": len(decision_history)}


# ─────────────────────────────────────────────
#  Zone Endpoints
# ─────────────────────────────────────────────

@app.get("/zones")
async def list_zones():
    return {"zones": zones.all_zones_as_dict(),
            "active_count": len(zones.get_active_zones())}


@app.post("/zones")
async def add_zone(req: ZoneCreateRequest):
    try:
        zone_type = ZoneType(req.zone_type)
    except ValueError:
        raise HTTPException(400, f"Invalid zone_type: {req.zone_type}")
    zone = zones.add_zone(req.name, zone_type, (req.x1, req.y1, req.x2, req.y2))
    return {"message": "Zone created", "zone": zone.to_dict()}


@app.delete("/zones/{zone_id}")
async def delete_zone(zone_id: str):
    if zones.remove_zone(zone_id):
        return {"message": f"Zone {zone_id} removed"}
    raise HTTPException(404, f"Zone {zone_id} not found")


@app.post("/zones/{zone_id}/toggle")
async def toggle_zone(zone_id: str):
    zone = zones.toggle_zone(zone_id)
    if zone:
        return {"message": f"Zone {'enabled' if zone.enabled else 'disabled'}",
                "zone": zone.to_dict()}
    raise HTTPException(404, f"Zone {zone_id} not found")


@app.post("/zones/reset")
async def reset_zones():
    zones.reset_to_defaults()
    return {"message": "Zones reset to defaults", "zones": zones.all_zones_as_dict()}


# ─────────────────────────────────────────────
#  Fleet Endpoints
# ─────────────────────────────────────────────

@app.get("/fleet")
async def get_fleet():
    return fleet.fleet_summary()


@app.get("/fleet/robots")
async def get_all_robots():
    return {"robots": fleet.all_robots()}


@app.get("/fleet/{agent_id}")
async def get_robot(agent_id: str):
    robot = fleet.get_robot(agent_id)
    if not robot:
        raise HTTPException(404, f"Robot {agent_id} not found")
    return robot.to_dict()


# ─────────────────────────────────────────────
#  Override Endpoints
# ─────────────────────────────────────────────

@app.get("/overrides/pending")
async def get_pending():
    return {"overrides": overrides.get_pending(),
            "count": len(overrides.get_pending())}


@app.post("/overrides/request")
async def request_override(req: OverrideRequestBody):
    ov = overrides.request_override(
        request_id=req.request_id,
        agent_id=req.agent_id,
        action_type=req.action_type,
        action_params=req.action_params,
        risk_score=req.risk_score,
        violations=req.violations,
        reasoning=req.reasoning,
    )
    await _broadcast({"type": "override_requested", **ov.to_dict()})
    return {"message": "Override request submitted", "override": ov.to_dict()}


@app.post("/overrides/{override_id}/approve")
async def approve_override(override_id: str, body: OverrideDecisionBody):
    success, message = overrides.approve(override_id, body.operator_id, body.justification)
    if not success:
        raise HTTPException(400, message)
    ov = overrides.get_override(override_id)
    await _broadcast({"type": "override_approved", "override_id": override_id})
    return {"message": message, "override": ov}


@app.post("/overrides/{override_id}/reject")
async def reject_override(override_id: str, body: OverrideDecisionBody):
    success, message = overrides.reject(override_id, body.operator_id, body.justification)
    if not success:
        raise HTTPException(400, message)
    return {"message": message}


@app.get("/overrides/audit")
async def get_audit_log(limit: int = 50):
    return {"audit_log": overrides.get_audit_log(limit),
            "total": len(overrides.audit_log)}


@app.get("/overrides/operators")
async def get_operators():
    return {"operators": overrides.get_operators()}


@app.get("/overrides/stats")
async def get_override_stats():
    return overrides.get_stats()


# ─────────────────────────────────────────────
#  WebSocket
# ─────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    ws_clients.append(websocket)
    logger.info(f"WS connected. Clients: {len(ws_clients)}")
    try:
        await websocket.send_text(json.dumps({
            "type":             "init",
            "fleet":            fleet.fleet_summary(),
            "zones":            zones.all_zones_as_dict(),
            "pending_overrides": len(overrides.get_pending()),
        }))
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in ws_clients:
            ws_clients.remove(websocket)
        logger.info(f"WS disconnected. Clients: {len(ws_clients)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)
