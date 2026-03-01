"""
SafeGuard Sentinel — Dashboard v2 (Streamlit Cloud Compatible)
Auto-detects if API is running. Falls back to built-in demo mode.
Tabs: Live Monitor | Zone Map | Fleet | Human Override | Audit Log
"""

import time
import random
import requests
from datetime import datetime
from collections import deque
import streamlit as st

# ─────────────────────────────────────────────
#  Page Config
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="SafeGuard Sentinel",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

API = "http://localhost:8000"

# ─────────────────────────────────────────────
#  CSS
# ─────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=IBM+Plex+Sans:wght@300;400;600;700&display=swap');
:root {
    --bg:#0a0c10; --bg2:#111520; --bg3:#181e2e; --border:#1e2a40;
    --allow:#00e5a0; --warn:#f5a623; --block:#ff3b5c;
    --neutral:#4a9eff; --text:#c8d8f0; --dim:#5a6a8a;
}
html,body,[class*="css"]{background:var(--bg)!important;color:var(--text)!important;font-family:'IBM Plex Sans',sans-serif;}
.stApp{background:var(--bg)!important;}
.sentinel-header{display:flex;align-items:center;gap:16px;padding:16px 0 8px;border-bottom:1px solid var(--border);margin-bottom:20px;}
.sentinel-logo{font-family:'Space Mono',monospace;font-size:1.5rem;font-weight:700;color:var(--neutral);letter-spacing:2px;}
.sentinel-sub{font-size:0.72rem;color:var(--dim);letter-spacing:3px;text-transform:uppercase;}
.online-badge{background:rgba(0,229,160,0.12);border:1px solid var(--allow);color:var(--allow);padding:3px 10px;border-radius:20px;font-size:0.72rem;font-family:'Space Mono',monospace;letter-spacing:1px;margin-left:auto;}
.demo-badge{background:rgba(245,166,35,0.12);border:1px solid #f5a623;color:#f5a623;padding:3px 10px;border-radius:20px;font-size:0.72rem;font-family:'Space Mono',monospace;letter-spacing:1px;margin-left:auto;}
.verdict-card{border-radius:12px;padding:20px 24px;border:1px solid var(--border);background:var(--bg2);position:relative;overflow:hidden;}
.verdict-card::before{content:'';position:absolute;top:0;left:0;width:4px;height:100%;}
.verdict-allow::before{background:var(--allow);}
.verdict-warn::before{background:var(--warn);}
.verdict-block::before{background:var(--block);}
.verdict-label{font-family:'Space Mono',monospace;font-size:1.3rem;font-weight:700;letter-spacing:3px;}
.allow-text{color:var(--allow);} .warn-text{color:var(--warn);} .block-text{color:var(--block);}
.risk-bar-bg{background:var(--bg3);border-radius:6px;height:8px;width:100%;overflow:hidden;margin-top:6px;}
.risk-bar{height:100%;border-radius:6px;}
.stat-box{background:var(--bg2);border:1px solid var(--border);border-radius:10px;padding:12px 16px;text-align:center;}
.stat-value{font-family:'Space Mono',monospace;font-size:1.8rem;font-weight:700;line-height:1;}
.stat-label{font-size:0.68rem;color:var(--dim);letter-spacing:2px;text-transform:uppercase;margin-top:4px;}
.log-row{background:var(--bg2);border:1px solid var(--border);border-radius:8px;padding:8px 12px;margin-bottom:5px;display:flex;align-items:center;gap:10px;font-size:0.82rem;}
.badge{font-family:'Space Mono',monospace;font-size:0.65rem;font-weight:700;padding:2px 7px;border-radius:4px;min-width:48px;text-align:center;letter-spacing:1px;}
.badge-allow{background:rgba(0,229,160,0.15);color:var(--allow);}
.badge-warn{background:rgba(245,166,35,0.15);color:var(--warn);}
.badge-block{background:rgba(255,59,92,0.15);color:var(--block);}
.section-title{font-family:'Space Mono',monospace;font-size:0.68rem;letter-spacing:3px;text-transform:uppercase;color:var(--dim);margin-bottom:8px;padding-bottom:5px;border-bottom:1px solid var(--border);}
.zone-pill{display:inline-block;font-size:0.7rem;padding:2px 8px;border-radius:4px;margin:2px;font-family:'Space Mono',monospace;font-weight:700;}
.zone-RESTRICTED{background:rgba(255,59,92,0.15);color:#ff3b5c;border:1px solid rgba(255,59,92,0.3);}
.zone-WARNING{background:rgba(245,166,35,0.15);color:#f5a623;border:1px solid rgba(245,166,35,0.3);}
.zone-SAFE{background:rgba(0,229,160,0.15);color:#00e5a0;border:1px solid rgba(0,229,160,0.3);}
.robot-card{background:var(--bg2);border:1px solid var(--border);border-radius:10px;padding:14px 18px;margin-bottom:8px;display:flex;align-items:center;gap:14px;}
.override-card{background:var(--bg2);border:2px solid rgba(255,59,92,0.4);border-radius:12px;padding:18px 22px;margin-bottom:12px;}
.demo-banner{background:rgba(245,166,35,0.08);border:1px solid rgba(245,166,35,0.3);border-radius:10px;padding:12px 18px;margin-bottom:16px;font-size:0.82rem;color:#f5a623;}
.stButton button{background:var(--bg3)!important;border:1px solid var(--border)!important;color:var(--text)!important;border-radius:8px!important;font-family:'Space Mono',monospace!important;font-size:0.72rem!important;letter-spacing:1px!important;}
.stButton button:hover{border-color:var(--neutral)!important;color:var(--neutral)!important;}
div[data-testid="stSidebarContent"]{background:var(--bg2)!important;border-right:1px solid var(--border)!important;}
.stTabs [data-baseweb="tab-list"]{background:var(--bg2)!important;border-bottom:1px solid var(--border)!important;}
.stTabs [data-baseweb="tab"]{background:transparent!important;color:var(--dim)!important;font-family:'Space Mono',monospace!important;font-size:0.72rem!important;letter-spacing:2px!important;}
.stTabs [aria-selected="true"]{color:var(--neutral)!important;border-bottom:2px solid var(--neutral)!important;}
.stSelectbox > div > div,.stTextInput > div > div{background:var(--bg3)!important;border-color:var(--border)!important;color:var(--text)!important;}
.stTextArea > div > div{background:var(--bg3)!important;border-color:var(--border)!important;}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  Demo Mode Engine
#  Runs entirely in-browser when API is offline
# ─────────────────────────────────────────────

DEMO_SCENARIOS = [
    {
        "action_type": "MOVE_FORWARD", "agent_id": "robot_01",
        "parameters": {"speed": 0.8, "distance_m": 1.0},
        "verdict": "ALLOW", "risk_score": 0.05,
        "violations": [],
        "llm_explanation": "The forward movement has been approved. The environment is clear with no humans detected nearby. Risk score is low at 5% — safe to proceed.",
        "recommended_alternative": None,
        "scene_summary": {"human_count": 0, "obstacle_count": 0, "nearest_human": None},
        "zone_summary": "All detections within safe zones",
        "zone_violations": 0, "zone_risk_multiplier": 1.0,
    },
    {
        "action_type": "NAVIGATE_TO", "agent_id": "robot_02",
        "parameters": {"speed": 1.2, "distance_m": 3.0, "direction": "north"},
        "verdict": "WARN", "risk_score": 0.55,
        "violations": [{"rule_id": "HUMAN_PROXIMITY_WARNING", "severity": "warning",
                        "description": "Human detected at MID range. Action NAVIGATE_TO requires reduced speed."}],
        "llm_explanation": "Navigation is proceeding with caution. One human detected at medium range — operator monitoring is recommended. Speed should be reduced below 1.0m/s.",
        "recommended_alternative": "Recalculate route avoiding occupied zones",
        "scene_summary": {"human_count": 1, "obstacle_count": 0, "nearest_human": "mid"},
        "zone_summary": "Detections in WARNING zone (risk ×1.4)",
        "zone_violations": 0, "zone_risk_multiplier": 1.4,
    },
    {
        "action_type": "MOVE_FORWARD", "agent_id": "robot_01",
        "parameters": {"speed": 2.8, "distance_m": 3.0},
        "verdict": "BLOCK", "risk_score": 0.95,
        "violations": [
            {"rule_id": "HUMAN_PROXIMITY_CRITICAL", "severity": "critical",
             "description": "Human detected at NEAR range. Action MOVE_FORWARD poses imminent collision risk."},
            {"rule_id": "EXCESSIVE_SPEED_HUMAN_PRESENT", "severity": "critical",
             "description": "Requested speed 2.8m/s exceeds 1.5m/s limit while 2 human(s) present."},
        ],
        "llm_explanation": "ACTION BLOCKED. Two humans detected at near range while speed 2.8m/s far exceeds the 1.5m/s safety limit. Risk score: 95%. Immediate halt required.",
        "recommended_alternative": "STOP and wait for humans to clear the path",
        "scene_summary": {"human_count": 2, "obstacle_count": 1, "nearest_human": "near"},
        "zone_summary": "Zone violations: HUMAN in Left Restricted Area",
        "zone_violations": 2, "zone_risk_multiplier": 2.0,
    },
    {
        "action_type": "ARM_EXTEND", "agent_id": "robot_03",
        "parameters": {"speed": 0.3, "angle_deg": 45},
        "verdict": "BLOCK", "risk_score": 0.80,
        "violations": [{"rule_id": "ARM_EXTEND_OBSTRUCTED", "severity": "critical",
                        "description": "Arm extension risky: 1 human(s), 2 obstacle(s) in scene."}],
        "llm_explanation": "Arm extension blocked. A human is present within the arm's range of motion. Extending the arm risks striking the person. Wait until the area is fully clear.",
        "recommended_alternative": "Wait until scene is clear, then re-attempt",
        "scene_summary": {"human_count": 1, "obstacle_count": 2, "nearest_human": "near"},
        "zone_summary": "All detections within safe zones",
        "zone_violations": 0, "zone_risk_multiplier": 1.0,
    },
    {
        "action_type": "STOP", "agent_id": "robot_02",
        "parameters": {"speed": 0},
        "verdict": "ALLOW", "risk_score": 0.0,
        "violations": [],
        "llm_explanation": "Emergency stop approved immediately. STOP commands are always safe and bypass all safety rules. The robot is now halted.",
        "recommended_alternative": None,
        "scene_summary": {"human_count": 1, "obstacle_count": 0, "nearest_human": "mid"},
        "zone_summary": "All detections within safe zones",
        "zone_violations": 0, "zone_risk_multiplier": 1.0,
    },
    {
        "action_type": "SPEED_INCREASE", "agent_id": "robot_01",
        "parameters": {"speed": 3.2},
        "verdict": "BLOCK", "risk_score": 0.85,
        "violations": [{"rule_id": "SPEED_INCREASE_BLOCKED", "severity": "critical",
                        "description": "Speed increase denied — scene is not clear."}],
        "llm_explanation": "Speed increase denied. A human is present in the environment and speed 3.2m/s would create an unacceptable collision risk. Maintain current speed.",
        "recommended_alternative": "Reduce speed to under 1.5m/s",
        "scene_summary": {"human_count": 1, "obstacle_count": 0, "nearest_human": "mid"},
        "zone_summary": "All detections within safe zones",
        "zone_violations": 0, "zone_risk_multiplier": 1.0,
    },
]

DEMO_ZONES = [
    {"id": "z1", "name": "Left Restricted Area",    "type": "RESTRICTED", "bbox": [0.0, 0.0, 0.25, 1.0], "enabled": True},
    {"id": "z2", "name": "Right Restricted Area",   "type": "RESTRICTED", "bbox": [0.75, 0.0, 1.0, 1.0], "enabled": True},
    {"id": "z3", "name": "Center Warning Corridor", "type": "WARNING",    "bbox": [0.25, 0.0, 0.75, 0.5], "enabled": True},
    {"id": "z4", "name": "Safe Operating Zone",     "type": "SAFE",       "bbox": [0.25, 0.5, 0.75, 1.0], "enabled": True},
]

DEMO_ROBOTS = [
    {"agent_id": "robot_01", "display_name": "Sentinel Alpha", "status": "OPERATING",
     "last_action": "MOVE_FORWARD", "last_verdict": "ALLOW", "last_risk_score": 0.05,
     "total_decisions": 12, "blocked_count": 3, "warned_count": 2, "allowed_count": 7,
     "block_rate": 0.25, "risk_level": "normal", "is_online": True, "location_hint": "Zone B"},
    {"agent_id": "robot_02", "display_name": "Sentinel Beta",  "status": "PAUSED",
     "last_action": "NAVIGATE_TO", "last_verdict": "BLOCK", "last_risk_score": 0.80,
     "total_decisions": 8, "blocked_count": 4, "warned_count": 2, "allowed_count": 2,
     "block_rate": 0.50, "risk_level": "critical", "is_online": True, "location_hint": "Zone A"},
    {"agent_id": "robot_03", "display_name": "Sentinel Gamma", "status": "IDLE",
     "last_action": "STOP", "last_verdict": "ALLOW", "last_risk_score": 0.0,
     "total_decisions": 5, "blocked_count": 1, "warned_count": 1, "allowed_count": 3,
     "block_rate": 0.20, "risk_level": "normal", "is_online": True, "location_hint": "Bay 3"},
]


# ─────────────────────────────────────────────
#  Session State
# ─────────────────────────────────────────────

defaults = {
    "decision_log": deque(maxlen=50),
    "stats": {"allow": 0, "warn": 0, "block": 0, "total": 0},
    "last_decision": None,
    "last_sim": 0.0,
    "demo_scenario_idx": 0,
    "demo_zones": list(DEMO_ZONES),
    "demo_override_log": [],
    "api_online": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────────
#  API / Demo Helpers
# ─────────────────────────────────────────────

def check_api():
    try:
        r = requests.get(f"{API}/health", timeout=1)
        return r.ok, r.json() if r.ok else {}
    except Exception:
        return False, {}

def api_get(path):
    try:
        r = requests.get(f"{API}{path}", timeout=3)
        return r.json() if r.ok else None
    except Exception:
        return None

def api_post(path, **kw):
    try:
        r = requests.post(f"{API}{path}", timeout=4, **kw)
        return r.json() if r.ok else None
    except Exception:
        return None

def api_delete(path):
    try:
        r = requests.delete(f"{API}{path}", timeout=3)
        return r.json() if r.ok else None
    except Exception:
        return None


def demo_evaluate(action_type, params, agent_id="robot_01"):
    """Simulate a safety decision locally when API is offline."""
    import uuid, time as t

    # Pick scenario based on action type
    scenario_map = {
        "STOP": 4, "MOVE_FORWARD": 0, "NAVIGATE_TO": 1,
        "ARM_EXTEND": 3, "SPEED_INCREASE": 5,
    }
    idx = scenario_map.get(action_type, st.session_state.demo_scenario_idx % len(DEMO_SCENARIOS))
    scenario = dict(DEMO_SCENARIOS[idx])

    # Override speed-based logic for demo realism
    speed = params.get("speed", 1.0)
    if action_type == "MOVE_FORWARD" and speed > 2.0:
        scenario = dict(DEMO_SCENARIOS[2])  # BLOCK - high speed
    elif action_type == "MOVE_FORWARD" and speed <= 1.0:
        scenario = dict(DEMO_SCENARIOS[0])  # ALLOW - normal speed

    scenario["request_id"] = str(uuid.uuid4())[:8]
    scenario["timestamp"] = t.time()
    scenario["action"] = {"action_type": action_type, "parameters": params, "agent_id": agent_id}
    scenario["agent_id"] = agent_id
    st.session_state.demo_scenario_idx += 1
    return scenario


def run_evaluation(action_type, params, agent_id="robot_01"):
    """Try API first, fall back to demo mode."""
    if st.session_state.api_online:
        result = api_post("/evaluate", json={"action_type": action_type,
                                              "parameters": params, "agent_id": agent_id})
        if result:
            return result
    return demo_evaluate(action_type, params, agent_id)


def record(result):
    if not result:
        return
    v = result.get("verdict", "ALLOW").lower()
    st.session_state.stats["total"] += 1
    st.session_state.stats[v] = st.session_state.stats.get(v, 0) + 1
    st.session_state.last_decision = result
    st.session_state.decision_log.appendleft(result)


def vc(v):
    return {"ALLOW": "allow", "WARN": "warn", "BLOCK": "block"}.get(v, "warn")

def rc(s):
    if s < 0.4:  return "#00e5a0"
    if s < 0.75: return "#f5a623"
    return "#ff3b5c"


# ─────────────────────────────────────────────
#  Check API on load
# ─────────────────────────────────────────────

online, health_data = check_api()
st.session_state.api_online = online
vision_mode = health_data.get("vision_mode", "demo") if online else "demo"


# ─────────────────────────────────────────────
#  Header
# ─────────────────────────────────────────────

pending_ov = health_data.get("pending_overrides", 0) if online else len([
    x for x in st.session_state.demo_override_log if x.get("status") == "PENDING"])

badge_class = "online-badge" if online else "demo-badge"
badge_text  = "● ONLINE · LIVE" if online else "● DEMO MODE · SIMULATION"

st.markdown(f"""
<div class="sentinel-header">
  <div>
    <div class="sentinel-logo">🛡️ SAFEGUARD SENTINEL</div>
    <div class="sentinel-sub">AI Governance Layer · Autonomous Robotics</div>
  </div>
  <div class="{badge_class}">{badge_text}</div>
</div>
""", unsafe_allow_html=True)

# Demo mode info banner
if not online:
    st.markdown("""
    <div class="demo-banner">
      ⚡ <strong>DEMO MODE</strong> — Running built-in simulation. All safety decisions, zones, fleet tracking,
      and override panel are fully functional. To connect a live backend, run
      <code>uvicorn api:app --port 8000</code> locally.
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  Sidebar
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown('<div class="section-title">⚡ Submit Action</div>', unsafe_allow_html=True)

    ACTIONS = ["MOVE_FORWARD", "MOVE_BACKWARD", "ROTATE", "GRIPPER_CLOSE",
               "GRIPPER_OPEN", "ARM_EXTEND", "SPEED_INCREASE", "NAVIGATE_TO", "STOP"]
    AGENTS  = ["robot_01", "robot_02", "robot_03"]

    action_type = st.selectbox("Action Type", ACTIONS)
    agent_id    = st.selectbox("Agent", AGENTS)
    speed       = st.slider("Speed (m/s)", 0.1, 3.0, 0.8, 0.1)
    distance    = st.slider("Distance (m)", 0.1, 5.0, 1.0, 0.1)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("▶ Evaluate", use_container_width=True):
            r = run_evaluation(action_type, {"speed": speed, "distance_m": distance}, agent_id)
            record(r)
            st.rerun()
    with c2:
        if st.button("⏹ STOP", use_container_width=True):
            r = run_evaluation("STOP", {"speed": 0}, agent_id)
            record(r)
            st.rerun()

    st.divider()
    st.markdown('<div class="section-title">🤖 Auto-Simulation</div>', unsafe_allow_html=True)
    auto_sim = st.toggle("Enable", value=False)
    sim_int  = st.slider("Interval (s)", 1, 8, 3)

    st.divider()
    st.markdown(f"""
    <div style="font-size:0.72rem;color:var(--dim);font-family:'Space Mono',monospace;line-height:2.2;">
    MODE: {"LIVE API" if online else "DEMO"}<br>
    VISION: {vision_mode.upper()}<br>
    ZONES: {len(st.session_state.demo_zones)}<br>
    ROBOTS: 3<br>
    EVALS: {st.session_state.stats["total"]}
    </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  Auto-Simulation
# ─────────────────────────────────────────────

SIM_POOL = [
    ("MOVE_FORWARD",   {"speed": random.uniform(0.5, 2.8), "distance_m": 1.0}),
    ("ARM_EXTEND",     {"speed": 0.3}),
    ("SPEED_INCREASE", {"speed": random.uniform(1.0, 3.2)}),
    ("NAVIGATE_TO",    {"speed": 1.0, "distance_m": 2.0}),
    ("STOP",           {"speed": 0}),
]

if auto_sim:
    now = time.time()
    if now - st.session_state.last_sim >= sim_int:
        at, p = random.choice(SIM_POOL)
        ag = random.choice(AGENTS)
        r  = run_evaluation(at, p, ag)
        record(r)
        st.session_state.last_sim = now


# ─────────────────────────────────────────────
#  Tabs
# ─────────────────────────────────────────────

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📡 LIVE MONITOR", "🗺️ ZONE MAP", "🤖 FLEET", "🔓 OVERRIDE", "📋 AUDIT LOG"
])


# ══════════════════════════════════════════════
#  TAB 1 — Live Monitor
# ══════════════════════════════════════════════

with tab1:
    left, right = st.columns([3, 2], gap="large")

    with left:
        # Stats
        stats = st.session_state.stats
        c1, c2, c3, c4 = st.columns(4)
        for col, val, lbl, color in [
            (c1, stats.get("allow", 0), "ALLOWED", "#00e5a0"),
            (c2, stats.get("warn",  0), "WARNED",  "#f5a623"),
            (c3, stats.get("block", 0), "BLOCKED", "#ff3b5c"),
            (c4, stats.get("total", 0), "TOTAL",   "#4a9eff"),
        ]:
            with col:
                st.markdown(f"""<div class="stat-box">
                    <div class="stat-value" style="color:{color};">{val}</div>
                    <div class="stat-label">{lbl}</div></div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-title">🔍 Latest Safety Decision</div>', unsafe_allow_html=True)

        dec = st.session_state.last_decision
        if dec:
            verdict = dec["verdict"]
            score   = dec["risk_score"]
            v_cls   = vc(verdict)
            color   = {"allow": "#00e5a0", "warn": "#f5a623", "block": "#ff3b5c"}[v_cls]
            icon    = {"allow": "✅", "warn": "⚠️", "block": "🛑"}[v_cls]
            act     = dec.get("action", {})
            agent   = act.get("agent_id", "") if isinstance(act, dict) else ""
            at      = act.get("action_type", "") if isinstance(act, dict) else ""
            zone_mult = dec.get("zone_risk_multiplier", 1.0)
            zone_sum  = dec.get("zone_summary", "")

            st.markdown(f"""
            <div class="verdict-card verdict-{v_cls}">
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <span class="verdict-label {v_cls}-text">{icon} {verdict}</span>
                <span style="font-family:'Space Mono',monospace;font-size:1.1rem;color:{color};">
                  RISK {score:.0%}</span>
              </div>
              <div class="risk-bar-bg">
                <div class="risk-bar" style="width:{score*100:.0f}%;background:{color};"></div>
              </div>
              <div style="margin-top:10px;font-size:0.75rem;color:var(--dim);font-family:'Space Mono',monospace;">
                {agent} · {at} · ID:{dec.get("request_id","—")}
                {"· Zone×"+f"{zone_mult:.1f}" if zone_mult > 1.0 else ""}
              </div>
              {f'<div style="margin-top:6px;font-size:0.75rem;color:#f5a623;">⚠ {zone_sum}</div>'
               if "violation" in zone_sum.lower() else ""}
            </div>""", unsafe_allow_html=True)

            if dec.get("llm_explanation"):
                st.markdown(f"""
                <div style="background:var(--bg2);border:1px solid var(--border);border-radius:10px;
                            padding:14px 18px;margin-top:8px;font-size:0.85rem;line-height:1.7;color:#8ab4d8;">
                  <span style="font-family:'Space Mono',monospace;font-size:0.62rem;color:var(--dim);
                               letter-spacing:2px;text-transform:uppercase;">🧠 AI Conscience</span>
                  <br><br>{dec["llm_explanation"]}
                </div>""", unsafe_allow_html=True)

            if dec.get("violations"):
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<div class="section-title">⚠️ Policy Violations</div>', unsafe_allow_html=True)
                for v in dec["violations"]:
                    vc2 = "#ff3b5c" if v["severity"] == "critical" else "#f5a623"
                    st.markdown(f"""
                    <div style="background:var(--bg3);border-left:3px solid {vc2};border-radius:6px;
                                padding:8px 12px;margin-bottom:5px;font-size:0.78rem;">
                      <span style="color:{vc2};font-family:'Space Mono',monospace;font-size:0.65rem;">
                        [{v["severity"].upper()}] {v["rule_id"]}</span><br>
                      <span style="color:var(--text);">{v["description"]}</span>
                    </div>""", unsafe_allow_html=True)

            if verdict == "BLOCK":
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🔓 Request Human Override", key="req_ov"):
                    entry = {
                        "override_id": f"ov_{len(st.session_state.demo_override_log)+1:03d}",
                        "request_id":  dec.get("request_id", ""),
                        "agent_id":    agent,
                        "action_type": at,
                        "risk_score":  score,
                        "violations":  dec.get("violations", []),
                        "reasoning":   dec.get("reasoning", ""),
                        "status":      "PENDING",
                        "created_at":  time.time(),
                        "expires_at":  time.time() + 120,
                    }
                    if online:
                        r = api_post("/overrides/request", json={
                            "request_id": dec.get("request_id", ""),
                            "agent_id": agent, "action_type": at,
                            "action_params": act.get("parameters", {}) if isinstance(act, dict) else {},
                            "risk_score": score, "violations": dec.get("violations", []),
                            "reasoning": dec.get("reasoning", ""),
                        })
                    st.session_state.demo_override_log.append(entry)
                    st.success(f"Override requested: {entry['override_id']}")

            if dec.get("recommended_alternative"):
                st.markdown(f"""
                <div style="background:rgba(74,158,255,0.08);border:1px solid rgba(74,158,255,0.25);
                            border-radius:8px;padding:10px 14px;margin-top:8px;font-size:0.82rem;">
                  <span style="color:#4a9eff;font-family:'Space Mono',monospace;font-size:0.62rem;
                               letter-spacing:2px;text-transform:uppercase;">💡 ALTERNATIVE</span><br>
                  <span style="color:var(--text);">{dec["recommended_alternative"]}</span>
                </div>""", unsafe_allow_html=True)

        else:
            st.markdown("""
            <div style="background:var(--bg2);border:1px dashed var(--border);border-radius:12px;
                        padding:40px;text-align:center;color:var(--dim);">
              <div style="font-size:2rem;">🤖</div>
              <div style="font-family:'Space Mono',monospace;font-size:0.78rem;letter-spacing:2px;margin-top:8px;">
                AWAITING ACTION SUBMISSION</div>
              <div style="font-size:0.75rem;margin-top:6px;">Use the sidebar or Quick Actions to evaluate a robot action</div>
            </div>""", unsafe_allow_html=True)

        # Decision Log
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-title">📋 Decision Log</div>', unsafe_allow_html=True)
        log = list(st.session_state.decision_log)[:10]
        for item in log:
            v    = item.get("verdict", "?")
            cls  = vc(v)
            ts   = datetime.fromtimestamp(item.get("timestamp", time.time())).strftime("%H:%M:%S")
            act2 = item.get("action", {})
            aname = act2.get("action_type", "?") if isinstance(act2, dict) else "?"
            ag2   = act2.get("agent_id",    "?") if isinstance(act2, dict) else "?"
            s2    = item.get("risk_score", 0)
            st.markdown(f"""<div class="log-row">
              <span class="badge badge-{cls}">{v}</span>
              <span style="color:#4a9eff;font-family:'Space Mono',monospace;font-size:0.72rem;">{aname}</span>
              <span style="color:var(--dim);font-size:0.72rem;">{ag2}</span>
              <span style="color:var(--dim);font-size:0.72rem;">Risk:{s2:.0%}</span>
              <span style="color:#3a4a6a;font-size:0.68rem;margin-left:auto;">{ts}</span>
            </div>""", unsafe_allow_html=True)

    with right:
        # Scene
        st.markdown('<div class="section-title">📷 Live Scene</div>', unsafe_allow_html=True)
        dec2 = st.session_state.last_decision
        scene = dec2.get("scene_summary", {}) if dec2 else {}
        humans    = scene.get("human_count", 0)
        obstacles = scene.get("obstacle_count", 0)
        nearest   = scene.get("nearest_human", "—") or "—"
        zone_viol = dec2.get("zone_violations", 0) if dec2 else 0
        hc  = "#ff3b5c" if humans > 0 else "#00e5a0"
        vc3 = "#ff3b5c" if zone_viol > 0 else "#5a6a8a"

        st.markdown(f"""
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px;">
          <div class="stat-box"><div class="stat-value" style="color:{hc};font-size:1.5rem;">{humans}</div>
            <div class="stat-label">Humans</div></div>
          <div class="stat-box"><div class="stat-value" style="color:#f5a623;font-size:1.5rem;">{obstacles}</div>
            <div class="stat-label">Obstacles</div></div>
          <div class="stat-box"><div class="stat-value" style="color:#4a9eff;font-size:0.9rem;padding-top:6px;">{nearest}</div>
            <div class="stat-label">Nearest</div></div>
          <div class="stat-box"><div class="stat-value" style="color:{vc3};font-size:1.5rem;">{zone_viol}</div>
            <div class="stat-label">Zone Viol.</div></div>
        </div>""", unsafe_allow_html=True)

        if dec2 and dec2.get("zone_summary"):
            zc = "#ff3b5c" if "violation" in dec2["zone_summary"].lower() else "#5a6a8a"
            st.markdown(f"""<div style="background:var(--bg3);border:1px solid var(--border);
                border-radius:8px;padding:8px 12px;font-size:0.75rem;color:{zc};margin-bottom:8px;">
                🗺️ {dec2["zone_summary"]}</div>""", unsafe_allow_html=True)

        # Quick actions
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-title">⚡ Quick Actions</div>', unsafe_allow_html=True)
        QA = [
            ("🚶 Move Forward", "MOVE_FORWARD",   {"speed": 1.0, "distance_m": 1.0}),
            ("🦾 ARM Extend",   "ARM_EXTEND",     {"speed": 0.3}),
            ("🛑 STOP",         "STOP",           {"speed": 0}),
            ("🏎 Fast Move",    "MOVE_FORWARD",   {"speed": 2.8, "distance_m": 3.0}),
        ]
        qcols = st.columns(2)
        for i, (lbl, at, p) in enumerate(QA):
            with qcols[i % 2]:
                if st.button(lbl, key=f"qa{i}", use_container_width=True):
                    r = run_evaluation(at, p, agent_id)
                    record(r)
                    st.rerun()


# ══════════════════════════════════════════════
#  TAB 2 — Zone Map
# ══════════════════════════════════════════════

with tab2:
    zone_list = st.session_state.demo_zones if not online else (
        (api_get("/zones") or {}).get("zones", st.session_state.demo_zones))

    col_l, col_r = st.columns([2, 3], gap="large")

    with col_l:
        st.markdown('<div class="section-title">🗺️ Active Zones</div>', unsafe_allow_html=True)

        for zone in zone_list:
            ztype  = zone["type"]
            zcolor = {"RESTRICTED": "#ff3b5c", "WARNING": "#f5a623", "SAFE": "#00e5a0"}.get(ztype, "#5a6a8a")
            enabled = zone.get("enabled", True)
            opacity = "1.0" if enabled else "0.4"
            bb = zone["bbox"]

            st.markdown(f"""
            <div style="background:var(--bg2);border:1px solid var(--border);border-left:3px solid {zcolor};
                        border-radius:8px;padding:10px 14px;margin-bottom:6px;opacity:{opacity};">
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="font-family:'Space Mono',monospace;font-size:0.78rem;color:{zcolor};">
                  {zone['name']}</span>
                <span class="zone-pill zone-{ztype}">{ztype[:3]}</span>
              </div>
              <div style="font-size:0.68rem;color:var(--dim);margin-top:4px;font-family:'Space Mono',monospace;">
                ({bb[0]:.2f},{bb[1]:.2f}) → ({bb[2]:.2f},{bb[3]:.2f})
              </div>
            </div>""", unsafe_allow_html=True)

            bc1, bc2 = st.columns(2)
            with bc1:
                lbl = "Disable" if enabled else "Enable"
                if st.button(lbl, key=f"tog_{zone['id']}", use_container_width=True):
                    for z in st.session_state.demo_zones:
                        if z["id"] == zone["id"]:
                            z["enabled"] = not z["enabled"]
                    if online:
                        api_post(f"/zones/{zone['id']}/toggle")
                    st.rerun()
            with bc2:
                if st.button("🗑 Remove", key=f"del_{zone['id']}", use_container_width=True):
                    st.session_state.demo_zones = [z for z in st.session_state.demo_zones
                                                    if z["id"] != zone["id"]]
                    if online:
                        api_delete(f"/zones/{zone['id']}")
                    st.rerun()

        if st.button("↺ Reset to Defaults", use_container_width=True):
            st.session_state.demo_zones = list(DEMO_ZONES)
            if online:
                api_post("/zones/reset")
            st.rerun()

    with col_r:
        st.markdown('<div class="section-title">➕ Add New Zone</div>', unsafe_allow_html=True)
        with st.form("add_zone_form"):
            zname     = st.text_input("Zone Name", placeholder="e.g. Assembly Area A")
            ztype_sel = st.selectbox("Zone Type", ["RESTRICTED", "WARNING", "SAFE"])
            st.markdown("**Bounding Box** (0.0 → 1.0 of frame)")
            zc1, zc2 = st.columns(2)
            with zc1:
                x1 = st.number_input("X1", 0.0, 1.0, 0.0, 0.05)
                y1 = st.number_input("Y1", 0.0, 1.0, 0.0, 0.05)
            with zc2:
                x2 = st.number_input("X2", 0.0, 1.0, 0.5, 0.05)
                y2 = st.number_input("Y2", 0.0, 1.0, 1.0, 0.05)
            if st.form_submit_button("Create Zone", use_container_width=True):
                if zname and x2 > x1 and y2 > y1:
                    new_zone = {
                        "id": f"z{len(st.session_state.demo_zones)+1}",
                        "name": zname, "type": ztype_sel,
                        "bbox": [x1, y1, x2, y2], "enabled": True,
                    }
                    st.session_state.demo_zones.append(new_zone)
                    if online:
                        api_post("/zones", json={"name": zname, "zone_type": ztype_sel,
                                                  "x1": x1, "y1": y1, "x2": x2, "y2": y2})
                    st.success(f"Zone '{zname}' created!")
                    st.rerun()
                else:
                    st.error("Invalid coordinates or missing name.")

        # Zone diagram
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-title">📐 Zone Diagram</div>', unsafe_allow_html=True)

        zone_bg = {"RESTRICTED": "rgba(255,59,92,0.22)", "WARNING": "rgba(245,166,35,0.18)", "SAFE": "rgba(0,229,160,0.15)"}
        zone_bc = {"RESTRICTED": "#ff3b5c", "WARNING": "#f5a623", "SAFE": "#00e5a0"}

        boxes_html = ""
        for zone in zone_list:
            if not zone.get("enabled", True):
                continue
            bb = zone["bbox"]
            lp = bb[0] * 100; tp = bb[1] * 100
            wp = (bb[2] - bb[0]) * 100; hp = (bb[3] - bb[1]) * 100
            bg = zone_bg.get(zone["type"], "rgba(90,90,90,0.2)")
            bc = zone_bc.get(zone["type"], "#5a6a8a")
            boxes_html += f"""<div style="position:absolute;left:{lp:.1f}%;top:{tp:.1f}%;
                width:{wp:.1f}%;height:{hp:.1f}%;background:{bg};border:2px solid {bc};
                border-radius:4px;display:flex;align-items:center;justify-content:center;">
              <span style="font-family:'Space Mono',monospace;font-size:0.55rem;color:{bc};
                           text-align:center;padding:2px;">{zone['name']}</span></div>"""

        st.markdown(f"""
        <div style="position:relative;width:100%;padding-bottom:56%;background:var(--bg3);
                    border:1px solid var(--border);border-radius:10px;overflow:hidden;">
          {boxes_html}
          <div style="position:absolute;bottom:6px;right:8px;font-family:'Space Mono',monospace;
                      font-size:0.55rem;color:var(--dim);">CAMERA FRAME (1.0 × 1.0)</div>
        </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  TAB 3 — Fleet
# ══════════════════════════════════════════════

with tab3:
    robots = DEMO_ROBOTS if not online else (api_get("/fleet") or {}).get("robots", DEMO_ROBOTS)

    # Update demo robots with latest decisions from session
    log_list = list(st.session_state.decision_log)
    for robot in robots:
        for item in log_list:
            act2 = item.get("action", {})
            if isinstance(act2, dict) and act2.get("agent_id") == robot["agent_id"]:
                robot["last_verdict"]    = item.get("verdict", robot["last_verdict"])
                robot["last_risk_score"] = item.get("risk_score", robot["last_risk_score"])
                robot["last_action"]     = act2.get("action_type", robot["last_action"])
                robot["total_decisions"] = robot.get("total_decisions", 0) + 1
                break

    # Fleet risk
    blocked_robots = [r for r in robots if r.get("last_verdict") == "BLOCK"]
    warned_robots  = [r for r in robots if r.get("last_verdict") == "WARN"]
    frisk  = "critical" if len(blocked_robots) >= 2 else "elevated" if blocked_robots else "normal"
    fscore = 0.85 if frisk == "critical" else 0.55 if frisk == "elevated" else 0.15
    fdesc  = f"{len(blocked_robots)} blocked, {len(warned_robots)} warned. Fleet operating with restrictions." \
             if blocked_robots else "All robots operating normally."
    fc = {"critical": "#ff3b5c", "elevated": "#f5a623", "normal": "#00e5a0"}.get(frisk, "#5a6a8a")

    st.markdown(f"""
    <div style="background:var(--bg2);border:2px solid {fc};border-radius:12px;
                padding:16px 22px;margin-bottom:20px;display:flex;
                justify-content:space-between;align-items:center;">
      <div>
        <div style="font-family:'Space Mono',monospace;font-size:0.65rem;color:var(--dim);
                    letter-spacing:2px;text-transform:uppercase;">FLEET RISK LEVEL</div>
        <div style="font-family:'Space Mono',monospace;font-size:1.4rem;font-weight:700;color:{fc};">
          {frisk.upper()}</div>
        <div style="font-size:0.8rem;color:var(--dim);margin-top:4px;">{fdesc}</div>
      </div>
      <div style="text-align:right;">
        <div style="font-family:'Space Mono',monospace;font-size:2rem;font-weight:700;color:{fc};">
          {fscore:.0%}</div>
        <div style="font-size:0.65rem;color:var(--dim);letter-spacing:2px;">FLEET SCORE</div>
      </div>
    </div>""", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""<div class="stat-box"><div class="stat-value" style="color:#00e5a0;">{len(robots)}</div>
            <div class="stat-label">Online</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="stat-box"><div class="stat-value" style="color:#f5a623;">{len(warned_robots)}</div>
            <div class="stat-label">Warning</div></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="stat-box"><div class="stat-value" style="color:#ff3b5c;">{len(blocked_robots)}</div>
            <div class="stat-label">Blocked</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">🤖 Robot Status</div>', unsafe_allow_html=True)

    for robot in robots:
        status  = robot.get("status", "IDLE")
        verdict = robot.get("last_verdict", "—")
        risk    = robot.get("last_risk_score", 0)
        rc_c    = rc(risk)
        sc_c    = {"OPERATING": "#00e5a0", "PAUSED": "#f5a623",
                   "EMERGENCY": "#ff3b5c", "IDLE": "#5a6a8a", "OFFLINE": "#333"}.get(status, "#5a6a8a")
        vbadge  = f'<span class="badge badge-{vc(verdict)}">{verdict}</span>' if verdict != "—" else ""

        st.markdown(f"""
        <div class="robot-card">
          <div style="width:10px;height:10px;border-radius:50%;background:{sc_c};
                      box-shadow:0 0 6px {sc_c};flex-shrink:0;"></div>
          <div style="flex:1;">
            <div style="display:flex;align-items:center;gap:8px;">
              <span style="font-family:'Space Mono',monospace;font-size:0.85rem;color:var(--text);">
                🟢 {robot.get("display_name","?")}</span>
              {vbadge}
            </div>
            <div style="font-size:0.7rem;color:var(--dim);margin-top:3px;font-family:'Space Mono',monospace;">
              {robot.get("agent_id","?")} · {status} · {robot.get("last_action","—")}
            </div>
          </div>
          <div style="text-align:right;min-width:80px;">
            <div style="font-family:'Space Mono',monospace;font-size:1.1rem;font-weight:700;color:{rc_c};">
              {risk:.0%}</div>
            <div style="font-size:0.62rem;color:var(--dim);">
              {robot.get("total_decisions",0)} evals · {robot.get("block_rate",0):.0%} block</div>
          </div>
        </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  TAB 4 — Human Override
# ══════════════════════════════════════════════

with tab4:
    OPERATORS = {
        "op_alice":   "Alice Chen (Safety Lead)",
        "op_bob":     "Bob Kumar (Floor Supervisor)",
        "op_charlie": "Charlie Diaz (Engineer)",
        "demo_op":    "Demo Operator",
    }

    pending = [x for x in st.session_state.demo_override_log
               if x.get("status") == "PENDING" and time.time() < x.get("expires_at", 0)]

    approved = len([x for x in st.session_state.demo_override_log if x.get("status") == "APPROVED"])
    rejected = len([x for x in st.session_state.demo_override_log if x.get("status") == "REJECTED"])
    expired  = len([x for x in st.session_state.demo_override_log if x.get("status") == "EXPIRED"])

    c1, c2, c3, c4 = st.columns(4)
    for col, val, lbl, color in [
        (c1, len(st.session_state.demo_override_log), "REQUESTED", "#4a9eff"),
        (c2, approved, "APPROVED", "#00e5a0"),
        (c3, rejected, "REJECTED", "#ff3b5c"),
        (c4, expired,  "EXPIRED",  "#5a6a8a"),
    ]:
        with col:
            st.markdown(f"""<div class="stat-box">
                <div class="stat-value" style="color:{color};font-size:1.5rem;">{val}</div>
                <div class="stat-label">{lbl}</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f'<div class="section-title">🔓 Pending Overrides ({len(pending)})</div>',
                unsafe_allow_html=True)

    if pending:
        for ov in pending:
            time_left = max(0, ov.get("expires_at", 0) - time.time())
            risk      = ov.get("risk_score", 0)
            rc_c      = rc(risk)
            mins = int(time_left // 60)
            secs = int(time_left % 60)

            st.markdown(f"""
            <div class="override-card">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div>
                  <div style="font-family:'Space Mono',monospace;font-size:0.65rem;
                               color:var(--dim);letter-spacing:2px;">OVERRIDE REQUEST</div>
                  <div style="font-family:'Space Mono',monospace;font-size:1rem;
                               color:#ff3b5c;margin-top:2px;">{ov["override_id"]}</div>
                </div>
                <div style="text-align:right;">
                  <div style="font-family:'Space Mono',monospace;font-size:0.75rem;color:#f5a623;">
                    ⏱ {mins}:{secs:02d} remaining</div>
                  <div style="font-family:'Space Mono',monospace;font-size:0.85rem;color:{rc_c};">
                    RISK {risk:.0%}</div>
                </div>
              </div>
              <div style="margin-top:10px;font-size:0.75rem;color:var(--dim);">
                AGENT: <span style="color:var(--text);">{ov["agent_id"]}</span> &nbsp;|&nbsp;
                ACTION: <span style="color:var(--text);">{ov["action_type"]}</span>
              </div>
            </div>""", unsafe_allow_html=True)

            with st.expander(f"🔑 Make Decision — {ov['override_id']}"):
                op_id = st.selectbox("Operator", list(OPERATORS.keys()),
                                     format_func=lambda x: OPERATORS.get(x, x),
                                     key=f"op_{ov['override_id']}")
                justification = st.text_area("Justification (required)",
                                             placeholder="Describe why you are approving or rejecting...",
                                             key=f"just_{ov['override_id']}")
                bc1, bc2 = st.columns(2)
                with bc1:
                    if st.button("✅ APPROVE", key=f"app_{ov['override_id']}", use_container_width=True):
                        if len(justification.strip()) >= 10:
                            ov["status"]        = "APPROVED"
                            ov["operator_id"]   = op_id
                            ov["justification"] = justification
                            ov["decided_at"]    = time.time()
                            if online:
                                api_post(f"/overrides/{ov['override_id']}/approve",
                                         json={"operator_id": op_id, "justification": justification})
                            st.success(f"Override approved by {OPERATORS[op_id]}")
                            st.rerun()
                        else:
                            st.error("Justification must be at least 10 characters")
                with bc2:
                    if st.button("🛑 REJECT", key=f"rej_{ov['override_id']}", use_container_width=True):
                        ov["status"]      = "REJECTED"
                        ov["operator_id"] = op_id
                        ov["decided_at"]  = time.time()
                        if online:
                            api_post(f"/overrides/{ov['override_id']}/reject",
                                     json={"operator_id": op_id,
                                           "justification": justification or "Block confirmed."})
                        st.info("Block confirmed.")
                        st.rerun()
    else:
        st.markdown("""
        <div style="background:var(--bg2);border:1px dashed var(--border);border-radius:12px;
                    padding:40px;text-align:center;">
          <div style="font-size:1.5rem;">✅</div>
          <div style="font-family:'Space Mono',monospace;font-size:0.75rem;color:var(--dim);
                      letter-spacing:2px;margin-top:8px;">NO PENDING OVERRIDES</div>
          <div style="font-size:0.75rem;color:var(--dim);margin-top:6px;">
            Click "Fast Move" or "ARM Extend" to trigger a BLOCK,
            then click "Request Human Override" on the Live Monitor tab.
          </div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">📜 Override Policy</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="card" style="font-size:0.78rem;color:var(--dim);line-height:2.2;">
      • Only BLOCKED actions can be overridden<br>
      • Risk score must be below 97% to be eligible<br>
      • Override requests expire after <span style="color:#f5a623;">2 minutes</span><br>
      • Operator ID and justification are mandatory<br>
      • All decisions are permanently logged in the audit trail
    </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  TAB 5 — Audit Log
# ══════════════════════════════════════════════

with tab5:
    audit = list(reversed(st.session_state.demo_override_log))
    if online:
        live_audit = (api_get("/overrides/audit?limit=50") or {}).get("audit_log", [])
        if live_audit:
            audit = live_audit

    event_colors = {"REQUESTED": "#4a9eff", "APPROVED": "#00e5a0",
                    "REJECTED": "#ff3b5c",  "EXPIRED": "#5a6a8a", "PENDING": "#f5a623"}

    st.markdown('<div class="section-title">📋 Override Audit Trail</div>', unsafe_allow_html=True)

    if audit:
        for entry in audit:
            event  = entry.get("status", entry.get("event", "?")).upper()
            ec     = event_colors.get(event, "#5a6a8a")
            ts     = datetime.fromtimestamp(entry.get("created_at", entry.get("timestamp", time.time()))).strftime("%H:%M:%S")
            just   = entry.get("justification", "—") or "—"
            op     = entry.get("operator_id", "system") or "system"
            risk   = entry.get("risk_score", 0)

            st.markdown(f"""
            <div class="log-row">
              <span class="badge" style="background:rgba(0,0,0,0.3);color:{ec};
                                          border:1px solid {ec};">{event}</span>
              <span style="color:#4a9eff;font-family:'Space Mono',monospace;font-size:0.72rem;">
                {entry.get("override_id","?")}</span>
              <span style="color:var(--text);font-size:0.75rem;">{entry.get("action_type","?")}</span>
              <span style="color:var(--dim);font-size:0.7rem;">Risk:{risk:.0%}</span>
              <span style="color:#8ab4d8;font-size:0.72rem;flex:1;overflow:hidden;text-overflow:ellipsis;">
                {op}: {just[:50] if just != "—" else "—"}</span>
              <span style="color:#3a4a6a;font-size:0.68rem;white-space:nowrap;">{ts}</span>
            </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""<div style="color:var(--dim);font-size:0.8rem;padding:20px;text-align:center;">
            No override activity yet. Trigger a BLOCK → Request Override → Approve or Reject it.
        </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  Auto-refresh
# ─────────────────────────────────────────────

time.sleep(2 if auto_sim else 3)
st.rerun()