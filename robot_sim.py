"""
SafeGuard Sentinel — Robot Agent Simulator
Simulates a robot agent continuously proposing actions to the SafeGuard API.
Useful for hackathon demos without real hardware.

Usage:  python robot_sim.py
"""

import time
import random
import requests
import json
from datetime import datetime

API_BASE = "http://localhost:8000"

SCENARIOS = [
    # (description, action_type, params)
    ("Robot navigating forward at normal speed",
     "MOVE_FORWARD", {"speed": 0.8, "distance_m": 1.0, "direction": "north"}),

    ("Robot accelerating to high speed",
     "MOVE_FORWARD", {"speed": 2.2, "distance_m": 3.0, "direction": "north"}),

    ("Robot attempting arm extension",
     "ARM_EXTEND", {"speed": 0.3, "angle_deg": 45}),

    ("Robot closing gripper to grab object",
     "GRIPPER_CLOSE", {"force_n": 5.0}),

    ("Robot requesting speed increase",
     "SPEED_INCREASE", {"speed": 3.0}),

    ("Robot performing safe rotation",
     "ROTATE", {"speed": 0.5, "angle_deg": 90}),

    ("Robot emergency stop",
     "STOP", {"speed": 0}),

    ("Robot navigating to target",
     "NAVIGATE_TO", {"speed": 1.0, "distance_m": 5.0, "direction": "east"}),
]

DIVIDER = "─" * 60


def send_action(action_type: str, params: dict, agent_id: str = "robot_sim_01") -> dict | None:
    try:
        r = requests.post(f"{API_BASE}/evaluate", json={
            "action_type": action_type,
            "parameters": params,
            "agent_id": agent_id,
        }, timeout=5)
        return r.json() if r.ok else None
    except requests.ConnectionError:
        print("⚠️  Cannot reach SafeGuard API. Is it running? (python -m uvicorn api:app)")
        return None


def print_decision(description: str, action_type: str, result: dict):
    verdict = result.get("verdict", "?")
    score   = result.get("risk_score", 0)
    ts      = datetime.now().strftime("%H:%M:%S")

    icons = {"ALLOW": "✅", "WARN": "⚠️ ", "BLOCK": "🛑"}
    icon  = icons.get(verdict, "❓")

    print(f"\n{DIVIDER}")
    print(f"[{ts}] 🤖 ROBOT: {description}")
    print(f"       ACTION : {action_type}")
    print(f"       VERDICT: {icon} {verdict}  |  RISK: {score:.0%}")
    print(f"       SCENE  : {result.get('scene_summary', {})}")

    if result.get("violations"):
        for v in result["violations"]:
            sev = "🔴" if v["severity"] == "critical" else "🟡"
            print(f"       {sev} {v['rule_id']}: {v['description'][:70]}")

    if result.get("llm_explanation"):
        print(f"       💬 {result['llm_explanation'][:120]}…")

    if result.get("recommended_alternative"):
        print(f"       💡 ALT: {result['recommended_alternative']}")


def run_demo_sequence():
    """Run through all scenarios once in a structured demo."""
    print(f"\n{'═'*60}")
    print("  SAFEGUARD SENTINEL — Robot Agent Simulator")
    print(f"{'═'*60}")
    print(f"  API: {API_BASE}")
    print(f"  Mode: Structured Demo Sequence")
    print(f"{'═'*60}\n")

    for description, action_type, params in SCENARIOS:
        result = send_action(action_type, params)
        if result:
            print_decision(description, action_type, result)
        time.sleep(2)

    print(f"\n{DIVIDER}")
    print("✅ Demo sequence complete.")


def run_continuous():
    """Continuously fire random actions (for live demo)."""
    print(f"\n{'═'*60}")
    print("  SAFEGUARD SENTINEL — Robot Agent Simulator")
    print(f"{'═'*60}")
    print("  Mode: Continuous Random (Ctrl+C to stop)")
    print(f"{'═'*60}\n")

    try:
        while True:
            desc, at, params = random.choice(SCENARIOS)
            result = send_action(at, params)
            if result:
                print_decision(desc, at, result)
            interval = random.uniform(1.5, 4.0)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n\n🛑 Simulator stopped.")


if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "demo"
    if mode == "continuous":
        run_continuous()
    else:
        run_demo_sequence()
