"""
SafeGuard Sentinel — Streamlit Dashboard
Real-time monitoring UI for the AI governance layer.
Run: streamlit run dashboard.py
"""

import time
import json
import base64
import random
import threading
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

API_BASE = "http://localhost:8000"

# ─────────────────────────────────────────────
#  Custom CSS
# ─────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=IBM+Plex+Sans:wght@300;400;600;700&display=swap');

:root {
    --bg:       #0a0c10;
    --bg2:      #111520;
    --bg3:      #181e2e;
    --border:   #1e2a40;
    --allow:    #00e5a0;
    --warn:     #f5a623;
    --block:    #ff3b5c;
    --neutral:  #4a9eff;
    --text:     #c8d8f0;
    --dim:      #5a6a8a;
    --accent:   #7b5ea7;
}

html, body, [class*="css"] {
    background-color: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'IBM Plex Sans', sans-serif;
}

.stApp { background: var(--bg) !important; }

/* Header */
.sentinel-header {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 20px 0 8px 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 24px;
}
.sentinel-logo {
    font-family: 'Space Mono', monospace;
    font-size: 1.6rem;
    font-weight: 700;
    color: var(--neutral);
    letter-spacing: 2px;
}
.sentinel-sub {
    font-size: 0.75rem;
    color: var(--dim);
    letter-spacing: 3px;
    text-transform: uppercase;
}
.online-badge {
    background: rgba(0,229,160,0.12);
    border: 1px solid var(--allow);
    color: var(--allow);
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-family: 'Space Mono', monospace;
    letter-spacing: 1px;
    margin-left: auto;
}

/* Verdict cards */
.verdict-card {
    border-radius: 12px;
    padding: 20px 24px;
    border: 1px solid var(--border);
    background: var(--bg2);
    position: relative;
    overflow: hidden;
}
.verdict-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 4px;
    height: 100%;
    border-radius: 12px 0 0 12px;
}
.verdict-allow::before { background: var(--allow); }
.verdict-warn::before  { background: var(--warn); }
.verdict-block::before { background: var(--block); }

.verdict-label {
    font-family: 'Space Mono', monospace;
    font-size: 1.4rem;
    font-weight: 700;
    letter-spacing: 3px;
}
.allow-text { color: var(--allow); }
.warn-text  { color: var(--warn); }
.block-text { color: var(--block); }

/* Risk meter */
.risk-bar-container {
    background: var(--bg3);
    border-radius: 6px;
    height: 10px;
    width: 100%;
    overflow: hidden;
    margin-top: 6px;
}
.risk-bar-fill {
    height: 100%;
    border-radius: 6px;
    transition: width 0.4s ease;
}

/* Stat boxes */
.stat-box {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px 18px;
    text-align: center;
}
.stat-value {
    font-family: 'Space Mono', monospace;
    font-size: 2rem;
    font-weight: 700;
    line-height: 1;
}
.stat-label {
    font-size: 0.7rem;
    color: var(--dim);
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-top: 4px;
}

/* Decision log row */
.log-row {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 0.85rem;
}
.log-badge {
    font-family: 'Space Mono', monospace;
    font-size: 0.68rem;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;
    min-width: 52px;
    text-align: center;
    letter-spacing: 1px;
}
.badge-allow { background: rgba(0,229,160,0.15); color: var(--allow); }
.badge-warn  { background: rgba(245,166,35,0.15); color: var(--warn); }
.badge-block { background: rgba(255,59,92,0.15);  color: var(--block); }

/* Violation pill */
.v-pill {
    display: inline-block;
    font-size: 0.7rem;
    padding: 2px 8px;
    border-radius: 20px;
    margin: 2px;
    font-family: 'Space Mono', monospace;
}
.v-critical { background: rgba(255,59,92,0.15); color: var(--block); border: 1px solid rgba(255,59,92,0.3); }
.v-warning  { background: rgba(245,166,35,0.15); color: var(--warn);  border: 1px solid rgba(245,166,35,0.3); }

/* Section headers */
.section-title {
    font-family: 'Space Mono', monospace;
    font-size: 0.72rem;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: var(--dim);
    margin-bottom: 10px;
    padding-bottom: 6px;
    border-bottom: 1px solid var(--border);
}

/* Scene frame */
.cam-frame {
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
    background: var(--bg3);
}

/* Override streamlit elements */
.stButton button {
    background: var(--bg3) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    border-radius: 8px !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.75rem !important;
    letter-spacing: 1px !important;
    padding: 8px 16px !important;
}
.stButton button:hover {
    border-color: var(--neutral) !important;
    color: var(--neutral) !important;
}
.stSelectbox > div, .stSlider > div, .stNumberInput > div {
    background: var(--bg2) !important;
}
div[data-testid="stSidebarContent"] {
    background: var(--bg2) !important;
    border-right: 1px solid var(--border) !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  Session State
# ─────────────────────────────────────────────

if "decision_log" not in st.session_state:
    st.session_state.decision_log = deque(maxlen=50)
if "stats"         not in st.session_state:
    st.session_state.stats = {"allow": 0, "warn": 0, "block": 0, "total": 0}
if "last_decision" not in st.session_state:
    st.session_state.last_decision = None
if "scene"         not in st.session_state:
    st.session_state.scene = None
if "scene_frame"   not in st.session_state:
    st.session_state.scene_frame = None

# ─────────────────────────────────────────────
#  API Helpers
# ─────────────────────────────────────────────

def fetch_scene():
    try:
        r = requests.get(f"{API_BASE}/scene", timeout=2)
        return r.json() if r.ok else None
    except Exception:
        return None


def fetch_history():
    try:
        r = requests.get(f"{API_BASE}/history?limit=20", timeout=2)
        return r.json().get("decisions", []) if r.ok else []
    except Exception:
        return []


def check_health():
    try:
        r = requests.get(f"{API_BASE}/health", timeout=1)
        return r.ok, r.json() if r.ok else {}
    except Exception:
        return False, {}


def evaluate_action(action_type: str, params: dict) -> dict | None:
    try:
        r = requests.post(f"{API_BASE}/evaluate", json={
            "action_type": action_type,
            "parameters": params,
            "agent_id": "dashboard_sim",
        }, timeout=5)
        return r.json() if r.ok else None
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def risk_color(score: float) -> str:
    if score < 0.4:  return "#00e5a0"
    if score < 0.75: return "#f5a623"
    return "#ff3b5c"


def verdict_class(verdict: str) -> str:
    return {"ALLOW": "allow", "WARN": "warn", "BLOCK": "block"}.get(verdict, "warn")

# ─────────────────────────────────────────────
#  Header
# ─────────────────────────────────────────────

online, health_data = check_health()
vision_mode = health_data.get("vision_mode", "unknown") if online else "offline"

st.markdown(f"""
<div class="sentinel-header">
    <div>
        <div class="sentinel-logo">🛡️ SAFEGUARD SENTINEL</div>
        <div class="sentinel-sub">AI Governance Layer for Autonomous Robotics</div>
    </div>
    <div class="online-badge">
        {"● ONLINE" if online else "● OFFLINE"} · {vision_mode.upper()}
    </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  Layout: Sidebar (Action Controls)
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown('<div class="section-title">⚡ Submit Robot Action</div>', unsafe_allow_html=True)

    ACTION_TYPES = [
        "MOVE_FORWARD", "MOVE_BACKWARD", "ROTATE",
        "GRIPPER_CLOSE", "GRIPPER_OPEN",
        "ARM_EXTEND", "SPEED_INCREASE",
        "NAVIGATE_TO", "STOP",
    ]
    action_type = st.selectbox("Action Type", ACTION_TYPES)
    speed       = st.slider("Speed (m/s)", 0.1, 3.0, 0.8, 0.1)
    distance    = st.slider("Distance (m)", 0.1, 5.0, 1.0, 0.1)
    direction   = st.selectbox("Direction", ["north", "south", "east", "west", "forward"])

    params = {"speed": speed, "distance_m": distance, "direction": direction}

    col1, col2 = st.columns(2)
    with col1:
        submit_btn = st.button("▶ Evaluate", use_container_width=True)
    with col2:
        stop_btn = st.button("⏹ STOP", use_container_width=True)

    st.divider()
    st.markdown('<div class="section-title">🤖 Auto-Simulation</div>', unsafe_allow_html=True)
    auto_sim = st.toggle("Enable auto-fire", value=False)
    sim_interval = st.slider("Interval (sec)", 1, 10, 3)

    st.divider()
    st.markdown('<div class="section-title">ℹ️ System Info</div>', unsafe_allow_html=True)
    if online:
        st.markdown(f"""
        <div style="font-size:0.75rem; color: #5a6a8a; font-family: 'Space Mono', monospace; line-height:2;">
        VISION: {vision_mode.upper()}<br>
        LLM: {"ENABLED" if health_data.get("llm_enabled") else "FALLBACK"}<br>
        DECISIONS: {health_data.get("decisions_logged", 0)}<br>
        </div>
        """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  Action Submission
# ─────────────────────────────────────────────

if submit_btn:
    with st.spinner("Evaluating…"):
        result = evaluate_action(action_type, params)
    if result:
        st.session_state.last_decision = result
        v = result["verdict"].lower()
        st.session_state.stats["total"] += 1
        st.session_state.stats[v] = st.session_state.stats.get(v, 0) + 1
        st.session_state.decision_log.appendleft(result)

if stop_btn:
    with st.spinner("Sending STOP…"):
        result = evaluate_action("STOP", {"speed": 0})
    if result:
        st.session_state.last_decision = result
        st.session_state.stats["total"] += 1
        st.session_state.stats["allow"] += 1
        st.session_state.decision_log.appendleft(result)

# Auto-simulation
if auto_sim:
    sim_actions = [
        ("MOVE_FORWARD",  {"speed": random.uniform(0.5, 2.5), "distance_m": 1.0}),
        ("ARM_EXTEND",    {"speed": 0.3}),
        ("SPEED_INCREASE",{"speed": random.uniform(1.0, 3.0)}),
        ("GRIPPER_CLOSE", {"speed": 0.2}),
        ("NAVIGATE_TO",   {"speed": 1.0, "distance_m": 2.0, "direction": "north"}),
    ]
    now = time.time()
    if "last_sim" not in st.session_state or now - st.session_state.last_sim >= sim_interval:
        at, p = random.choice(sim_actions)
        result = evaluate_action(at, p)
        if result:
            st.session_state.last_decision = result
            v = result["verdict"].lower()
            st.session_state.stats["total"] += 1
            st.session_state.stats[v] = st.session_state.stats.get(v, 0) + 1
            st.session_state.decision_log.appendleft(result)
        st.session_state.last_sim = now

# ─────────────────────────────────────────────
#  Main Content Area
# ─────────────────────────────────────────────

left_col, right_col = st.columns([3, 2], gap="large")

with left_col:
    # ── Latest Decision ──────────────────────────────────────
    st.markdown('<div class="section-title">🔍 Latest Safety Decision</div>', unsafe_allow_html=True)

    dec = st.session_state.last_decision
    if dec:
        verdict  = dec["verdict"]
        score    = dec["risk_score"]
        v_cls    = verdict_class(verdict)
        v_color  = {"allow": "#00e5a0", "warn": "#f5a623", "block": "#ff3b5c"}[v_cls]
        icon     = {"allow": "✅", "warn": "⚠️", "block": "🛑"}[v_cls]

        st.markdown(f"""
        <div class="verdict-card verdict-{v_cls}">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="verdict-label {v_cls}-text">{icon} {verdict}</span>
                <span style="font-family:'Space Mono',monospace; font-size:1.1rem; color:{v_color};">
                    RISK {score:.0%}
                </span>
            </div>
            <div class="risk-bar-container" style="margin-top:10px;">
                <div class="risk-bar-fill" style="width:{score*100:.0f}%; background:{v_color};"></div>
            </div>
            <div style="margin-top:12px; font-size:0.8rem; color:#5a6a8a; font-family:'Space Mono',monospace;">
                ACTION: {dec.get("action",{}).get("action_type","") if isinstance(dec.get("action"), dict) else dec.get("action_type","N/A")} &nbsp;|&nbsp;
                ID: {dec.get("request_id","—")}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # LLM Explanation
        if dec.get("llm_explanation"):
            st.markdown(f"""
            <div style="background:var(--bg2); border:1px solid var(--border); border-radius:10px;
                        padding:14px 18px; margin-top:10px; font-size:0.87rem; line-height:1.7;
                        color: #8ab4d8;">
                <span style="font-family:'Space Mono',monospace; font-size:0.65rem;
                             color: var(--dim); letter-spacing:2px; text-transform:uppercase;">
                    🧠 AI Conscience Explanation
                </span><br><br>
                {dec['llm_explanation']}
            </div>
            """, unsafe_allow_html=True)

        # Violations
        if dec.get("violations"):
            st.markdown('<br>', unsafe_allow_html=True)
            st.markdown('<div class="section-title">⚠️ Policy Violations</div>', unsafe_allow_html=True)
            pills = ""
            for v in dec["violations"]:
                cls = "v-critical" if v["severity"] == "critical" else "v-warning"
                pills += f'<span class="v-pill {cls}">{v["rule_id"]}</span> '
            st.markdown(pills, unsafe_allow_html=True)
            for v in dec["violations"]:
                st.markdown(f"""
                <div style="font-size:0.78rem; color:#7a8aaa; margin:4px 0 2px 8px;">
                    ↳ {v['description']}
                </div>""", unsafe_allow_html=True)

        if dec.get("recommended_alternative"):
            st.markdown(f"""
            <div style="background:rgba(74,158,255,0.08); border:1px solid rgba(74,158,255,0.25);
                        border-radius:8px; padding:10px 14px; margin-top:10px; font-size:0.82rem;">
                <span style="color:#4a9eff; font-family:'Space Mono',monospace; font-size:0.65rem;
                             letter-spacing:2px; text-transform:uppercase;">💡 RECOMMENDED</span><br>
                <span style="color:#c8d8f0;">{dec['recommended_alternative']}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background:var(--bg2); border:1px dashed var(--border); border-radius:12px;
                    padding:40px; text-align:center; color: var(--dim);">
            <div style="font-size:2rem; margin-bottom:10px;">🤖</div>
            <div style="font-family:'Space Mono',monospace; font-size:0.8rem; letter-spacing:2px;">
                AWAITING ACTION SUBMISSION
            </div>
            <div style="font-size:0.75rem; margin-top:6px;">
                Use the sidebar to submit a robot action for evaluation
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Decision History ─────────────────────────────────────
    st.markdown('<br>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📋 Decision Log</div>', unsafe_allow_html=True)

    if st.session_state.decision_log:
        for item in list(st.session_state.decision_log)[:10]:
            v   = item["verdict"]
            cls = verdict_class(v)
            ts  = datetime.fromtimestamp(item["timestamp"]).strftime("%H:%M:%S")
            action_name = "N/A"
            if isinstance(item.get("action"), dict):
                action_name = item["action"].get("action_type", "N/A")
            score = item["risk_score"]

            st.markdown(f"""
            <div class="log-row">
                <span class="log-badge badge-{cls}">{v}</span>
                <span style="font-family:'Space Mono',monospace; font-size:0.75rem; color:#4a9eff;">
                    {action_name}
                </span>
                <span style="color:#5a6a8a; font-size:0.75rem;">Risk: {score:.0%}</span>
                <span style="color:#3a4a6a; font-size:0.72rem; margin-left:auto;">{ts}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        history = fetch_history()
        if history:
            for item in history[:8]:
                v   = item["verdict"]
                cls = verdict_class(v)
                ts  = datetime.fromtimestamp(item["timestamp"]).strftime("%H:%M:%S")
                score = item["risk_score"]
                st.markdown(f"""
                <div class="log-row">
                    <span class="log-badge badge-{cls}">{v}</span>
                    <span style="color:#5a6a8a; font-size:0.75rem;">Risk: {score:.0%}</span>
                    <span style="color:#3a4a6a; font-size:0.72rem; margin-left:auto;">{ts}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown('<div style="color:var(--dim); font-size:0.8rem;">No decisions yet.</div>',
                        unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
with right_col:
    # ── Session Stats ────────────────────────────────────────
    st.markdown('<div class="section-title">📊 Session Stats</div>', unsafe_allow_html=True)
    stats = st.session_state.stats

    c1, c2, c3 = st.columns(3)
    boxes = [
        (c1, stats.get("allow", 0), "ALLOWED", "#00e5a0"),
        (c2, stats.get("warn",  0), "WARNED",  "#f5a623"),
        (c3, stats.get("block", 0), "BLOCKED", "#ff3b5c"),
    ]
    for col, val, label, color in boxes:
        with col:
            st.markdown(f"""
            <div class="stat-box">
                <div class="stat-value" style="color:{color};">{val}</div>
                <div class="stat-label">{label}</div>
            </div>""", unsafe_allow_html=True)

    total = stats.get("total", 0)
    if total > 0:
        block_rate = stats.get("block", 0) / total
        color = risk_color(block_rate)
        st.markdown(f"""
        <div style="margin-top:10px; background:var(--bg2); border:1px solid var(--border);
                    border-radius:10px; padding:12px 16px;">
            <div style="display:flex; justify-content:space-between; font-size:0.75rem;">
                <span style="color:var(--dim); font-family:'Space Mono',monospace; letter-spacing:1px;">
                    BLOCK RATE
                </span>
                <span style="color:{color}; font-family:'Space Mono',monospace;">{block_rate:.0%}</span>
            </div>
            <div class="risk-bar-container" style="margin-top:6px;">
                <div class="risk-bar-fill" style="width:{block_rate*100:.0f}%; background:{color};"></div>
            </div>
            <div style="text-align:center; font-size:0.72rem; color:var(--dim); margin-top:6px;">
                {total} total evaluations this session
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Live Scene ───────────────────────────────────────────
    st.markdown('<br>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📷 Live Scene</div>', unsafe_allow_html=True)

    scene_data = fetch_scene()
    if scene_data and not scene_data.get("error"):
        humans = scene_data.get("human_count", 0)
        obstacles = scene_data.get("obstacle_count", 0)
        nearest = scene_data.get("nearest_human", "None")
        h_color = "#ff3b5c" if humans > 0 else "#00e5a0"

        st.markdown(f"""
        <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; margin-bottom:10px;">
            <div class="stat-box">
                <div class="stat-value" style="color:{h_color}; font-size:1.5rem;">{humans}</div>
                <div class="stat-label">Humans</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" style="color:#f5a623; font-size:1.5rem;">{obstacles}</div>
                <div class="stat-label">Obstacles</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" style="color:#4a9eff; font-size:0.9rem; padding-top:4px;">
                    {nearest or "—"}
                </div>
                <div class="stat-label">Nearest</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Detections list
        detections = scene_data.get("detections", [])
        if detections:
            det_html = ""
            for d in detections:
                color = "#ff3b5c" if d["is_human"] else "#f5a623"
                det_html += f"""
                <div style="display:flex; justify-content:space-between; align-items:center;
                            padding:5px 10px; background:var(--bg3); border-radius:6px; margin-bottom:4px;">
                    <span style="color:{color}; font-family:'Space Mono',monospace; font-size:0.75rem;">
                        {'👤' if d['is_human'] else '📦'} {d['label']}
                    </span>
                    <span style="color:var(--dim); font-size:0.72rem;">
                        {d['confidence']:.0%} · {d['distance']}
                    </span>
                </div>"""
            st.markdown(det_html, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background:var(--bg2); border:1px solid var(--border); border-radius:10px;
                    padding:20px; text-align:center; color:var(--dim); font-size:0.78rem;">
            Scene data unavailable. Ensure API is running.
        </div>
        """, unsafe_allow_html=True)

    # ── Quick Actions ────────────────────────────────────────
    st.markdown('<br>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">⚡ Quick Actions</div>', unsafe_allow_html=True)

    qa_cols = st.columns(2)
    quick_actions = [
        ("🚶 Move Forward",  "MOVE_FORWARD",  {"speed": 1.0, "distance_m": 1.0}),
        ("🤖 ARM Extend",    "ARM_EXTEND",    {"speed": 0.3}),
        ("🔴 EMERGENCY STOP","STOP",           {"speed": 0}),
        ("🏎️ Fast Move",    "MOVE_FORWARD",  {"speed": 2.8, "distance_m": 3.0}),
    ]
    for i, (label, at, p) in enumerate(quick_actions):
        with qa_cols[i % 2]:
            if st.button(label, key=f"qa_{i}", use_container_width=True):
                result = evaluate_action(at, p)
                if result:
                    st.session_state.last_decision = result
                    v = result["verdict"].lower()
                    st.session_state.stats["total"] += 1
                    st.session_state.stats[v] = st.session_state.stats.get(v, 0) + 1
                    st.session_state.decision_log.appendleft(result)
                    st.rerun()

# ─────────────────────────────────────────────
#  Auto-refresh
# ─────────────────────────────────────────────

if auto_sim:
    time.sleep(sim_interval)
    st.rerun()
else:
    time.sleep(2)
    st.rerun()
