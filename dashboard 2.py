"""
SafeGuard Sentinel — Dashboard v2
Tabs: Live Monitor | Zone Map | Fleet | Human Override | Audit Log
"""

import time
import json
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
    --neutral:#4a9eff; --text:#c8d8f0; --dim:#5a6a8a; --accent:#7b5ea7;
}
html,body,[class*="css"]{background:var(--bg)!important;color:var(--text)!important;font-family:'IBM Plex Sans',sans-serif;}
.stApp{background:var(--bg)!important;}
.sentinel-header{display:flex;align-items:center;gap:16px;padding:16px 0 8px;border-bottom:1px solid var(--border);margin-bottom:20px;}
.sentinel-logo{font-family:'Space Mono',monospace;font-size:1.5rem;font-weight:700;color:var(--neutral);letter-spacing:2px;}
.sentinel-sub{font-size:0.72rem;color:var(--dim);letter-spacing:3px;text-transform:uppercase;}
.online-badge{background:rgba(0,229,160,0.12);border:1px solid var(--allow);color:var(--allow);padding:3px 10px;border-radius:20px;font-size:0.72rem;font-family:'Space Mono',monospace;letter-spacing:1px;margin-left:auto;}
.card{background:var(--bg2);border:1px solid var(--border);border-radius:10px;padding:16px 20px;margin-bottom:10px;}
.verdict-card{border-radius:12px;padding:20px 24px;border:1px solid var(--border);background:var(--bg2);position:relative;overflow:hidden;}
.verdict-card::before{content:'';position:absolute;top:0;left:0;width:4px;height:100%;border-radius:12px 0 0 12px;}
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
.robot-status{width:10px;height:10px;border-radius:50%;display:inline-block;}
.status-OPERATING{background:#00e5a0;box-shadow:0 0 6px #00e5a0;}
.status-IDLE{background:#5a6a8a;}
.status-PAUSED{background:#f5a623;box-shadow:0 0 6px #f5a623;}
.status-EMERGENCY{background:#ff3b5c;box-shadow:0 0 8px #ff3b5c;animation:pulse 1s infinite;}
.status-OFFLINE{background:#333;}
@keyframes pulse{0%,100%{opacity:1;}50%{opacity:0.4;}}
.override-card{background:var(--bg2);border:2px solid rgba(255,59,92,0.4);border-radius:12px;padding:18px 22px;margin-bottom:12px;}
.override-timer{font-family:'Space Mono',monospace;font-size:0.75rem;color:#f5a623;}
.stButton button{background:var(--bg3)!important;border:1px solid var(--border)!important;color:var(--text)!important;border-radius:8px!important;font-family:'Space Mono',monospace!important;font-size:0.72rem!important;letter-spacing:1px!important;}
.stButton button:hover{border-color:var(--neutral)!important;color:var(--neutral)!important;}
div[data-testid="stSidebarContent"]{background:var(--bg2)!important;border-right:1px solid var(--border)!important;}
.stTabs [data-baseweb="tab-list"]{background:var(--bg2)!important;border-bottom:1px solid var(--border)!important;gap:4px;}
.stTabs [data-baseweb="tab"]{background:transparent!important;color:var(--dim)!important;font-family:'Space Mono',monospace!important;font-size:0.72rem!important;letter-spacing:2px!important;border-radius:8px 8px 0 0!important;}
.stTabs [aria-selected="true"]{color:var(--neutral)!important;border-bottom:2px solid var(--neutral)!important;}
.stSelectbox > div > div, .stTextInput > div > div{background:var(--bg3)!important;border-color:var(--border)!important;color:var(--text)!important;}
.stTextArea > div > div{background:var(--bg3)!important;border-color:var(--border)!important;}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  Session State
# ─────────────────────────────────────────────

defaults = {
    "decision_log": deque(maxlen=50),
    "stats": {"allow": 0, "warn": 0, "block": 0, "total": 0},
    "last_decision": None,
    "last_sim": 0.0,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────────
#  API Helpers
# ─────────────────────────────────────────────

def api(method, path, **kwargs):
    try:
        r = getattr(requests, method)(f"{API}{path}", timeout=4, **kwargs)
        return r.json() if r.ok else None
    except Exception:
        return None

def get(path): return api("get", path)
def post(path, **kw): return api("post", path, **kw)
def delete(path): return api("delete", path)

def record_decision(result):
    if not result: return
    v = result.get("verdict", "ALLOW").lower()
    st.session_state.stats["total"] += 1
    st.session_state.stats[v] = st.session_state.stats.get(v, 0) + 1
    st.session_state.last_decision = result
    st.session_state.decision_log.appendleft(result)

def vc(v): return {"ALLOW":"allow","WARN":"warn","BLOCK":"block"}.get(v,"warn")
def rc(s):
    if s < 0.4: return "#00e5a0"
    if s < 0.75: return "#f5a623"
    return "#ff3b5c"


# ─────────────────────────────────────────────
#  Header
# ─────────────────────────────────────────────

health = get("/health") or {}
online = bool(health)
vision_mode = health.get("vision_mode", "offline")
pending_ov = health.get("pending_overrides", 0)

ov_badge = f' · <span style="color:#ff3b5c">⚠ {pending_ov} OVERRIDE{"S" if pending_ov!=1 else ""}</span>' if pending_ov else ""

st.markdown(f"""
<div class="sentinel-header">
  <div>
    <div class="sentinel-logo">🛡️ SAFEGUARD SENTINEL</div>
    <div class="sentinel-sub">AI Governance Layer · Autonomous Robotics</div>
  </div>
  <div class="online-badge">{"● ONLINE" if online else "● OFFLINE"} · {vision_mode.upper()}{ov_badge}</div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  Sidebar
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown('<div class="section-title">⚡ Submit Action</div>', unsafe_allow_html=True)

    ACTIONS = ["MOVE_FORWARD","MOVE_BACKWARD","ROTATE","GRIPPER_CLOSE",
               "GRIPPER_OPEN","ARM_EXTEND","SPEED_INCREASE","NAVIGATE_TO","STOP"]
    AGENTS  = ["robot_01","robot_02","robot_03","dashboard_sim"]

    action_type = st.selectbox("Action Type", ACTIONS)
    agent_id    = st.selectbox("Agent", AGENTS)
    speed       = st.slider("Speed (m/s)", 0.1, 3.0, 0.8, 0.1)
    distance    = st.slider("Distance (m)", 0.1, 5.0, 1.0, 0.1)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("▶ Evaluate", use_container_width=True):
            r = post("/evaluate", json={"action_type": action_type, "agent_id": agent_id,
                                        "parameters": {"speed": speed, "distance_m": distance}})
            record_decision(r)
            st.rerun()
    with c2:
        if st.button("⏹ STOP", use_container_width=True):
            r = post("/evaluate", json={"action_type": "STOP", "agent_id": agent_id,
                                        "parameters": {"speed": 0}})
            record_decision(r)
            st.rerun()

    st.divider()
    st.markdown('<div class="section-title">🤖 Auto-Sim</div>', unsafe_allow_html=True)
    auto_sim = st.toggle("Enable", value=False)
    sim_int  = st.slider("Interval (s)", 1, 8, 3)

    st.divider()
    st.markdown(f"""
    <div style="font-size:0.72rem;color:var(--dim);font-family:'Space Mono',monospace;line-height:2.2;">
    VISION: {vision_mode.upper()}<br>
    LLM: {"ON" if health.get("llm_enabled") else "OFF"}<br>
    ZONES: {health.get("active_zones",0)}<br>
    ROBOTS: {health.get("online_robots",0)}<br>
    OVERRIDES: {pending_ov}
    </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  Auto-Simulation
# ─────────────────────────────────────────────

SIM_ACTIONS = [
    ("MOVE_FORWARD",   {"speed": random.uniform(0.5,2.5),"distance_m":1.0}),
    ("ARM_EXTEND",     {"speed":0.3}),
    ("SPEED_INCREASE", {"speed": random.uniform(1.0,3.2)}),
    ("GRIPPER_CLOSE",  {"speed":0.2}),
    ("NAVIGATE_TO",    {"speed":1.0,"distance_m":2.0,"direction":"north"}),
]

if auto_sim:
    now = time.time()
    if now - st.session_state.last_sim >= sim_int:
        at, p = random.choice(SIM_ACTIONS)
        ag = random.choice(["robot_01","robot_02","robot_03"])
        r  = post("/evaluate", json={"action_type":at,"agent_id":ag,"parameters":p})
        record_decision(r)
        st.session_state.last_sim = now


# ─────────────────────────────────────────────
#  Tabs
# ─────────────────────────────────────────────

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📡 LIVE MONITOR",
    "🗺️ ZONE MAP",
    "🤖 FLEET",
    "🔓 OVERRIDE",
    "📋 AUDIT LOG",
])


# ══════════════════════════════════════════════
#  TAB 1 — Live Monitor
# ══════════════════════════════════════════════

with tab1:
    left, right = st.columns([3,2], gap="large")

    with left:
        # Stats row
        stats = st.session_state.stats
        c1,c2,c3,c4 = st.columns(4)
        for col, val, lbl, color in [
            (c1, stats.get("allow",0), "ALLOWED", "#00e5a0"),
            (c2, stats.get("warn", 0), "WARNED",  "#f5a623"),
            (c3, stats.get("block",0), "BLOCKED", "#ff3b5c"),
            (c4, stats.get("total",0), "TOTAL",   "#4a9eff"),
        ]:
            with col:
                st.markdown(f"""<div class="stat-box">
                    <div class="stat-value" style="color:{color};">{val}</div>
                    <div class="stat-label">{lbl}</div></div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-title">🔍 Latest Decision</div>', unsafe_allow_html=True)

        dec = st.session_state.last_decision
        if dec:
            verdict = dec["verdict"]
            score   = dec["risk_score"]
            v_cls   = vc(verdict)
            color   = {"allow":"#00e5a0","warn":"#f5a623","block":"#ff3b5c"}[v_cls]
            icon    = {"allow":"✅","warn":"⚠️","block":"🛑"}[v_cls]
            act     = dec.get("action",{})
            agent   = act.get("agent_id","") if isinstance(act,dict) else ""
            at      = act.get("action_type","") if isinstance(act,dict) else ""
            zone_mult = dec.get("zone_risk_multiplier", 1.0)
            zone_sum  = dec.get("zone_summary","")

            st.markdown(f"""
            <div class="verdict-card verdict-{v_cls}">
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <span class="verdict-label {v_cls}-text">{icon} {verdict}</span>
                <span style="font-family:'Space Mono',monospace;font-size:1.1rem;color:{color};">
                  RISK {score:.0%}
                </span>
              </div>
              <div class="risk-bar-bg"><div class="risk-bar" style="width:{score*100:.0f}%;background:{color};"></div></div>
              <div style="margin-top:10px;font-size:0.75rem;color:var(--dim);font-family:'Space Mono',monospace;">
                {agent} · {at} · ID:{dec.get("request_id","—")}
                {"· Zone×"+f"{zone_mult:.1f}" if zone_mult > 1.0 else ""}
              </div>
              {f'<div style="margin-top:6px;font-size:0.75rem;color:#f5a623;">⚠ {zone_sum}</div>' if "violation" in zone_sum.lower() else ""}
            </div>""", unsafe_allow_html=True)

            # LLM explanation
            if dec.get("llm_explanation"):
                st.markdown(f"""
                <div style="background:var(--bg2);border:1px solid var(--border);border-radius:10px;
                            padding:14px 18px;margin-top:8px;font-size:0.85rem;line-height:1.7;color:#8ab4d8;">
                  <span style="font-family:'Space Mono',monospace;font-size:0.62rem;color:var(--dim);
                               letter-spacing:2px;text-transform:uppercase;">🧠 AI Conscience</span><br><br>
                  {dec["llm_explanation"]}
                </div>""", unsafe_allow_html=True)

            # Violations
            if dec.get("violations"):
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<div class="section-title">⚠️ Violations</div>', unsafe_allow_html=True)
                for v in dec["violations"]:
                    cls = "v-critical" if v["severity"]=="critical" else "v-warning"
                    color2 = "#ff3b5c" if v["severity"]=="critical" else "#f5a623"
                    st.markdown(f"""
                    <div style="background:var(--bg3);border-left:3px solid {color2};border-radius:6px;
                                padding:8px 12px;margin-bottom:5px;font-size:0.78rem;">
                      <span style="color:{color2};font-family:'Space Mono',monospace;font-size:0.65rem;">
                        [{v["severity"].upper()}] {v["rule_id"]}
                      </span><br>
                      <span style="color:var(--text);">{v["description"]}</span>
                    </div>""", unsafe_allow_html=True)

            # Override button for BLOCK
            if verdict == "BLOCK":
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🔓 Request Human Override", key="req_ov_btn"):
                    r = post("/overrides/request", json={
                        "request_id":  dec.get("request_id",""),
                        "agent_id":    agent,
                        "action_type": at,
                        "action_params": act.get("parameters",{}) if isinstance(act,dict) else {},
                        "risk_score":  score,
                        "violations":  dec.get("violations",[]),
                        "reasoning":   dec.get("reasoning",""),
                    })
                    if r:
                        st.success(f"Override requested: {r.get('override',{}).get('override_id','')}")
                    else:
                        st.error("Failed to submit override")

            # Alternative
            if dec.get("recommended_alternative"):
                st.markdown(f"""
                <div style="background:rgba(74,158,255,0.08);border:1px solid rgba(74,158,255,0.25);
                            border-radius:8px;padding:10px 14px;margin-top:8px;font-size:0.82rem;">
                  <span style="color:#4a9eff;font-family:'Space Mono',monospace;font-size:0.62rem;
                               letter-spacing:2px;text-transform:uppercase;">💡 ALTERNATIVE</span><br>
                  <span style="color:var(--text);">{dec["recommended_alternative"]}</span>
                </div>""", unsafe_allow_html=True)

        else:
            st.markdown("""<div style="background:var(--bg2);border:1px dashed var(--border);
                border-radius:12px;padding:40px;text-align:center;color:var(--dim);">
                <div style="font-size:2rem;">🤖</div>
                <div style="font-family:'Space Mono',monospace;font-size:0.78rem;letter-spacing:2px;margin-top:8px;">
                AWAITING ACTION SUBMISSION</div></div>""", unsafe_allow_html=True)

        # Decision log
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-title">📋 Decision Log</div>', unsafe_allow_html=True)
        log = list(st.session_state.decision_log)[:10]
        if not log:
            log = (get("/history") or {}).get("decisions", [])[:8]
        for item in log:
            v   = item.get("verdict","?")
            cls = vc(v)
            ts  = datetime.fromtimestamp(item.get("timestamp",0)).strftime("%H:%M:%S")
            act2 = item.get("action",{})
            aname = act2.get("action_type","?") if isinstance(act2,dict) else "?"
            ag2   = act2.get("agent_id","?") if isinstance(act2,dict) else "?"
            score2 = item.get("risk_score",0)
            st.markdown(f"""<div class="log-row">
              <span class="badge badge-{cls}">{v}</span>
              <span style="color:#4a9eff;font-family:'Space Mono',monospace;font-size:0.72rem;">{aname}</span>
              <span style="color:var(--dim);font-size:0.72rem;">{ag2}</span>
              <span style="color:var(--dim);font-size:0.72rem;">Risk:{score2:.0%}</span>
              <span style="color:#3a4a6a;font-size:0.68rem;margin-left:auto;">{ts}</span>
            </div>""", unsafe_allow_html=True)

    with right:
        # Scene
        st.markdown('<div class="section-title">📷 Live Scene</div>', unsafe_allow_html=True)
        scene = get("/scene") or {}
        humans    = scene.get("human_count", 0)
        obstacles = scene.get("obstacle_count", 0)
        nearest   = scene.get("nearest_human", "—")
        zone_viol = scene.get("zone_violations", 0)
        hc = "#ff3b5c" if humans>0 else "#00e5a0"
        vc2 = "#ff3b5c" if zone_viol>0 else "#5a6a8a"

        st.markdown(f"""
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px;">
          <div class="stat-box"><div class="stat-value" style="color:{hc};font-size:1.5rem;">{humans}</div><div class="stat-label">Humans</div></div>
          <div class="stat-box"><div class="stat-value" style="color:#f5a623;font-size:1.5rem;">{obstacles}</div><div class="stat-label">Obstacles</div></div>
          <div class="stat-box"><div class="stat-value" style="color:#4a9eff;font-size:0.9rem;padding-top:6px;">{nearest or "—"}</div><div class="stat-label">Nearest</div></div>
          <div class="stat-box"><div class="stat-value" style="color:{vc2};font-size:1.5rem;">{zone_viol}</div><div class="stat-label">Zone Viol.</div></div>
        </div>""", unsafe_allow_html=True)

        if scene.get("zone_summary"):
            zcolor = "#ff3b5c" if "violation" in scene["zone_summary"].lower() else "#5a6a8a"
            st.markdown(f"""<div style="background:var(--bg3);border:1px solid var(--border);
                border-radius:8px;padding:8px 12px;font-size:0.75rem;color:{zcolor};margin-bottom:8px;">
                🗺️ {scene["zone_summary"]}</div>""", unsafe_allow_html=True)

        for d in scene.get("detections", []):
            color3 = "#ff3b5c" if d["is_human"] else "#f5a623"
            st.markdown(f"""<div style="display:flex;justify-content:space-between;align-items:center;
                padding:5px 10px;background:var(--bg3);border-radius:6px;margin-bottom:4px;">
                <span style="color:{color3};font-family:'Space Mono',monospace;font-size:0.72rem;">
                {'👤' if d['is_human'] else '📦'} {d['label']}</span>
                <span style="color:var(--dim);font-size:0.7rem;">{d['confidence']:.0%} · {d['distance']}</span>
            </div>""", unsafe_allow_html=True)

        # Quick actions
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-title">⚡ Quick Actions</div>', unsafe_allow_html=True)
        qcols = st.columns(2)
        QA = [("🚶 Forward","MOVE_FORWARD",{"speed":1.0}),
              ("🦾 ARM Extend","ARM_EXTEND",{"speed":0.3}),
              ("🛑 STOP","STOP",{"speed":0}),
              ("🏎 Fast Fwd","MOVE_FORWARD",{"speed":2.8})]
        for i,(lbl,at,p) in enumerate(QA):
            with qcols[i%2]:
                if st.button(lbl, key=f"qa{i}", use_container_width=True):
                    r = post("/evaluate", json={"action_type":at,"agent_id":agent_id,"parameters":p})
                    record_decision(r)
                    st.rerun()


# ══════════════════════════════════════════════
#  TAB 2 — Zone Map
# ══════════════════════════════════════════════

with tab2:
    zone_data = get("/zones") or {"zones":[],"active_count":0}
    zone_list = zone_data.get("zones", [])

    col_left, col_right = st.columns([2,3], gap="large")

    with col_left:
        st.markdown('<div class="section-title">🗺️ Active Zones</div>', unsafe_allow_html=True)

        for zone in zone_list:
            ztype  = zone["type"]
            zcolor = {"RESTRICTED":"#ff3b5c","WARNING":"#f5a623","SAFE":"#00e5a0"}.get(ztype,"#5a6a8a")
            enabled = zone.get("enabled", True)
            opacity = "1.0" if enabled else "0.4"
            bb = zone["bbox"]

            st.markdown(f"""
            <div style="background:var(--bg2);border:1px solid var(--border);border-left:3px solid {zcolor};
                        border-radius:8px;padding:10px 14px;margin-bottom:6px;opacity:{opacity};">
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="font-family:'Space Mono',monospace;font-size:0.78rem;color:{zcolor};">
                  {zone['name']}
                </span>
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
                    post(f"/zones/{zone['id']}/toggle")
                    st.rerun()
            with bc2:
                if st.button("🗑 Remove", key=f"del_{zone['id']}", use_container_width=True):
                    delete(f"/zones/{zone['id']}")
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("↺ Reset to Defaults", use_container_width=True):
            post("/zones/reset")
            st.rerun()

    with col_right:
        st.markdown('<div class="section-title">➕ Add New Zone</div>', unsafe_allow_html=True)
        with st.form("add_zone_form"):
            zname = st.text_input("Zone Name", placeholder="e.g. Assembly Area A")
            ztype_sel = st.selectbox("Zone Type", ["RESTRICTED","WARNING","SAFE"])
            st.markdown("**Bounding Box** (normalized 0.0 → 1.0 of frame width/height)")
            zc1,zc2 = st.columns(2)
            with zc1:
                x1 = st.number_input("X1 (left)",  0.0, 1.0, 0.0, 0.05)
                y1 = st.number_input("Y1 (top)",   0.0, 1.0, 0.0, 0.05)
            with zc2:
                x2 = st.number_input("X2 (right)", 0.0, 1.0, 0.5, 0.05)
                y2 = st.number_input("Y2 (bottom)",0.0, 1.0, 1.0, 0.05)

            if st.form_submit_button("Create Zone", use_container_width=True):
                if zname and x2 > x1 and y2 > y1:
                    r = post("/zones", json={"name":zname,"zone_type":ztype_sel,
                                             "x1":x1,"y1":y1,"x2":x2,"y2":y2})
                    if r:
                        st.success(f"Zone '{zname}' created!")
                        st.rerun()
                else:
                    st.error("Invalid zone coordinates or missing name.")

        # Visual zone diagram
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-title">📐 Zone Diagram (normalized frame)</div>', unsafe_allow_html=True)

        zone_colors_css = {"RESTRICTED":"rgba(255,59,92,0.25)","WARNING":"rgba(245,166,35,0.2)","SAFE":"rgba(0,229,160,0.15)"}
        zone_borders    = {"RESTRICTED":"#ff3b5c","WARNING":"#f5a623","SAFE":"#00e5a0"}

        boxes_html = ""
        for zone in zone_list:
            if not zone.get("enabled",True):
                continue
            bb    = zone["bbox"]
            left_pct  = bb[0]*100
            top_pct   = bb[1]*100
            width_pct  = (bb[2]-bb[0])*100
            height_pct = (bb[3]-bb[1])*100
            bg    = zone_colors_css.get(zone["type"],"rgba(90,90,90,0.2)")
            bc    = zone_borders.get(zone["type"],"#5a6a8a")
            boxes_html += f"""
            <div style="position:absolute;left:{left_pct:.1f}%;top:{top_pct:.1f}%;
                        width:{width_pct:.1f}%;height:{height_pct:.1f}%;
                        background:{bg};border:2px solid {bc};border-radius:4px;
                        display:flex;align-items:center;justify-content:center;">
              <span style="font-family:'Space Mono',monospace;font-size:0.55rem;
                           color:{bc};text-align:center;padding:2px;">{zone['name']}</span>
            </div>"""

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
    fleet_data = get("/fleet") or {}
    robots     = fleet_data.get("robots", [])

    # Fleet risk banner
    frisk = fleet_data.get("fleet_risk_level","normal")
    fscore = fleet_data.get("fleet_risk_score",0)
    fdesc  = fleet_data.get("fleet_description","")
    fc = {"normal":"#00e5a0","elevated":"#f5a623","critical":"#ff3b5c"}.get(frisk,"#5a6a8a")

    st.markdown(f"""
    <div style="background:var(--bg2);border:2px solid {fc};border-radius:12px;
                padding:16px 22px;margin-bottom:20px;display:flex;
                justify-content:space-between;align-items:center;">
      <div>
        <div style="font-family:'Space Mono',monospace;font-size:0.65rem;color:var(--dim);
                    letter-spacing:2px;text-transform:uppercase;">FLEET RISK LEVEL</div>
        <div style="font-family:'Space Mono',monospace;font-size:1.4rem;
                    font-weight:700;color:{fc};">{frisk.upper()}</div>
        <div style="font-size:0.8rem;color:var(--dim);margin-top:4px;">{fdesc}</div>
      </div>
      <div style="text-align:right;">
        <div style="font-family:'Space Mono',monospace;font-size:2rem;font-weight:700;color:{fc};">
          {fscore:.0%}</div>
        <div style="font-size:0.65rem;color:var(--dim);letter-spacing:2px;">FLEET SCORE</div>
      </div>
    </div>""", unsafe_allow_html=True)

    # Fleet stats
    c1,c2,c3 = st.columns(3)
    with c1:
        st.markdown(f"""<div class="stat-box">
            <div class="stat-value" style="color:#00e5a0;">{fleet_data.get("active_robots",0)}</div>
            <div class="stat-label">Online</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="stat-box">
            <div class="stat-value" style="color:#f5a623;">{fleet_data.get("robots_in_warning",0)}</div>
            <div class="stat-label">Warning</div></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="stat-box">
            <div class="stat-value" style="color:#ff3b5c;">{fleet_data.get("robots_blocked",0)}</div>
            <div class="stat-label">Blocked</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">🤖 Robot Status</div>', unsafe_allow_html=True)

    if robots:
        for robot in robots:
            status   = robot.get("status","IDLE")
            verdict  = robot.get("last_verdict","—")
            risk     = robot.get("last_risk_score",0)
            rc_color = rc(risk)
            sc_color = {"OPERATING":"#00e5a0","PAUSED":"#f5a623",
                        "EMERGENCY":"#ff3b5c","IDLE":"#5a6a8a","OFFLINE":"#333"}.get(status,"#5a6a8a")
            vbadge   = f'<span class="badge badge-{vc(verdict)}">{verdict}</span>' if verdict != "—" else ""
            online_dot = "🟢" if robot.get("is_online") else "⚫"

            st.markdown(f"""
            <div class="robot-card">
              <div style="width:10px;height:10px;border-radius:50%;background:{sc_color};
                          box-shadow:0 0 6px {sc_color};flex-shrink:0;"></div>
              <div style="flex:1;">
                <div style="display:flex;align-items:center;gap:8px;">
                  <span style="font-family:'Space Mono',monospace;font-size:0.85rem;
                               color:var(--text);">{online_dot} {robot.get("display_name","?")}</span>
                  {vbadge}
                </div>
                <div style="font-size:0.7rem;color:var(--dim);margin-top:3px;font-family:'Space Mono',monospace;">
                  {robot.get("agent_id","?")} · {status}
                  · Action:{robot.get("last_action","—")}
                </div>
              </div>
              <div style="text-align:right;min-width:80px;">
                <div style="font-family:'Space Mono',monospace;font-size:1.1rem;
                            font-weight:700;color:{rc_color};">{risk:.0%}</div>
                <div style="font-size:0.62rem;color:var(--dim);">
                  {robot.get("total_decisions",0)} evals
                  · {robot.get("block_rate",0):.0%} block
                </div>
              </div>
            </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""<div style="color:var(--dim);font-size:0.8rem;padding:20px;text-align:center;">
            No robots online yet. Submit actions from the sidebar.</div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  TAB 4 — Human Override
# ══════════════════════════════════════════════

with tab4:
    pending_data = get("/overrides/pending") or {"overrides":[],"count":0}
    pending      = pending_data.get("overrides", [])
    operators    = {o["id"]:o["name"] for o in (get("/overrides/operators") or {}).get("operators",[])}
    ov_stats     = get("/overrides/stats") or {}

    # Stats
    c1,c2,c3,c4 = st.columns(4)
    for col, val, lbl, color in [
        (c1, ov_stats.get("total_requested",0), "REQUESTED", "#4a9eff"),
        (c2, ov_stats.get("total_approved", 0), "APPROVED",  "#00e5a0"),
        (c3, ov_stats.get("total_rejected", 0), "REJECTED",  "#ff3b5c"),
        (c4, ov_stats.get("total_expired",  0), "EXPIRED",   "#5a6a8a"),
    ]:
        with col:
            st.markdown(f"""<div class="stat-box">
                <div class="stat-value" style="color:{color};font-size:1.5rem;">{val}</div>
                <div class="stat-label">{lbl}</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f'<div class="section-title">🔓 Pending Override Requests ({len(pending)})</div>',
                unsafe_allow_html=True)

    if pending:
        for ov in pending:
            time_left = ov.get("time_remaining", 0)
            risk      = ov.get("risk_score", 0)
            rc_c      = rc(risk)
            mins = int(time_left // 60)
            secs = int(time_left  % 60)

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
                  <div class="override-timer">⏱ {mins}:{secs:02d} remaining</div>
                  <div style="font-family:'Space Mono',monospace;font-size:0.85rem;color:{rc_c};">
                    RISK {risk:.0%}</div>
                </div>
              </div>
              <div style="margin-top:10px;display:grid;grid-template-columns:1fr 1fr;gap:8px;
                          font-size:0.75rem;color:var(--dim);">
                <div>AGENT: <span style="color:var(--text);">{ov["agent_id"]}</span></div>
                <div>ACTION: <span style="color:var(--text);">{ov["action_type"]}</span></div>
              </div>
            </div>""", unsafe_allow_html=True)

            # Violations summary
            if ov.get("violations"):
                for v in ov["violations"][:2]:
                    vc_color2 = "#ff3b5c" if v["severity"]=="critical" else "#f5a623"
                    st.markdown(f"""<div style="background:var(--bg3);border-left:2px solid {vc_color2};
                        border-radius:4px;padding:6px 10px;font-size:0.72rem;margin-bottom:4px;">
                        <span style="color:{vc_color2};">[{v["severity"].upper()}]</span>
                        {v["description"][:80]}</div>""", unsafe_allow_html=True)

            # Operator decision form
            with st.expander(f"🔑 Make Decision — {ov['override_id']}"):
                op_id = st.selectbox(
                    "Operator", list(operators.keys()),
                    format_func=lambda x: operators.get(x, x),
                    key=f"op_{ov['override_id']}"
                )
                justification = st.text_area(
                    "Justification (required)",
                    placeholder="Describe why you are approving or rejecting this override...",
                    key=f"just_{ov['override_id']}"
                )
                bc1, bc2 = st.columns(2)
                with bc1:
                    if st.button("✅ APPROVE Override", key=f"approve_{ov['override_id']}",
                                 use_container_width=True):
                        if len(justification.strip()) >= 10:
                            r = post(f"/overrides/{ov['override_id']}/approve",
                                     json={"operator_id":op_id,"justification":justification})
                            if r:
                                st.success(r.get("message","Approved"))
                                st.rerun()
                            else:
                                st.error("Failed to approve (check risk score limit)")
                        else:
                            st.error("Justification must be at least 10 characters")
                with bc2:
                    if st.button("🛑 REJECT Override", key=f"reject_{ov['override_id']}",
                                 use_container_width=True):
                        r = post(f"/overrides/{ov['override_id']}/reject",
                                 json={"operator_id":op_id,
                                       "justification":justification or "Block confirmed by operator."})
                        if r:
                            st.info(r.get("message","Rejected"))
                            st.rerun()
    else:
        st.markdown("""<div style="background:var(--bg2);border:1px dashed var(--border);
            border-radius:12px;padding:40px;text-align:center;">
            <div style="font-size:1.5rem;">✅</div>
            <div style="font-family:'Space Mono',monospace;font-size:0.75rem;color:var(--dim);
                        letter-spacing:2px;margin-top:8px;">NO PENDING OVERRIDES</div>
            <div style="font-size:0.75rem;color:var(--dim);margin-top:6px;">
              Submit a MOVE_FORWARD or ARM_EXTEND while humans are present to trigger a BLOCK,
              then click "Request Human Override" on the Live Monitor tab.
            </div>
        </div>""", unsafe_allow_html=True)

    # Override rules info
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">📜 Override Policy</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="card" style="font-size:0.78rem;color:var(--dim);line-height:2;">
      • Only BLOCKED actions can be overridden<br>
      • Risk score must be below 97% to be eligible<br>
      • Override requests expire after <span style="color:#f5a623;">2 minutes</span><br>
      • Operator ID and justification are mandatory<br>
      • All decisions are logged in the immutable audit trail
    </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  TAB 5 — Audit Log
# ══════════════════════════════════════════════

with tab5:
    audit_data = get("/overrides/audit?limit=50") or {"audit_log":[]}
    audit_log  = audit_data.get("audit_log", [])

    st.markdown('<div class="section-title">📋 Override Audit Trail</div>', unsafe_allow_html=True)

    event_colors = {
        "REQUESTED":"#4a9eff", "APPROVED":"#00e5a0",
        "REJECTED":"#ff3b5c",  "EXPIRED":"#5a6a8a",
    }

    if audit_log:
        for entry in audit_log:
            ec     = event_colors.get(entry.get("event",""),"#5a6a8a")
            ts     = datetime.fromtimestamp(entry.get("timestamp",0)).strftime("%H:%M:%S")
            just   = entry.get("justification","—")
            op     = entry.get("operator_id","system")
            risk   = entry.get("risk_score",0)

            st.markdown(f"""
            <div class="log-row">
              <span class="badge" style="background:rgba(0,0,0,0.3);color:{ec};
                                          border:1px solid {ec};">{entry.get("event","?")}</span>
              <span style="color:#4a9eff;font-family:'Space Mono',monospace;font-size:0.72rem;">
                {entry.get("override_id","?")}</span>
              <span style="color:var(--text);font-size:0.75rem;">{entry.get("action_type","?")}</span>
              <span style="color:var(--dim);font-size:0.7rem;">Risk:{risk:.0%}</span>
              <span style="color:#8ab4d8;font-size:0.72rem;flex:1;overflow:hidden;text-overflow:ellipsis;">
                {op}: {just[:50] if just and just != "—" else "—"}</span>
              <span style="color:#3a4a6a;font-size:0.68rem;white-space:nowrap;">{ts}</span>
            </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""<div style="color:var(--dim);font-size:0.8rem;padding:20px;text-align:center;">
            No override activity yet. Trigger a BLOCK and request an override to see entries here.
        </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  Auto-refresh
# ─────────────────────────────────────────────

time.sleep(2 if auto_sim else 3)
st.rerun()
