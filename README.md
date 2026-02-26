# 🛡️ SafeGuard Sentinel
### AI Governance Layer for Autonomous Robotics

A real-time AI "conscience layer" that intercepts robot actions, analyzes the
environment with computer vision, and applies safety policies before allowing
execution — making autonomous systems explainably safe.

---

## Architecture

```
Robot Agent
    │
    ▼  POST /evaluate
┌─────────────────────────────────────────────────┐
│            FastAPI Intercept Layer (api.py)      │
│                                                  │
│  ┌──────────────────┐  ┌────────────────────┐   │
│  │  Vision Module   │  │  Safety Policy     │   │
│  │  (vision_module) │  │  Engine            │   │
│  │                  │  │  (safety_engine)   │   │
│  │  YOLOv8 + OpenCV │  │  8 rule checks     │   │
│  │  Human detection │  │  Risk scoring      │   │
│  │  Distance zones  │  │  ALLOW/WARN/BLOCK  │   │
│  └──────────────────┘  └────────────────────┘   │
│                                                  │
│  ┌──────────────────┐                           │
│  │  LLM Reasoner    │  ← Optional (Claude API)  │
│  │  (llm_reasoner)  │                           │
│  │  Natural lang.   │                           │
│  │  explanations    │                           │
│  └──────────────────┘                           │
│                                                  │
│  ┌──────────────────────────────┐               │
│  │  WebSocket broadcast         │ → Dashboard   │
│  └──────────────────────────────┘               │
└─────────────────────────────────────────────────┘
    │
    ▼  JSON: verdict + risk_score + reasoning
Robot executes ONLY if verdict = "ALLOW"
```

---

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. (Optional) Set your Anthropic API key for LLM explanations
```bash
export ANTHROPIC_API_KEY=your_key_here
```

### 3. Start the API server
```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Start the dashboard (new terminal)
```bash
streamlit run dashboard.py
```

### 5. Run the robot simulator (new terminal)
```bash
# Structured demo sequence (recommended for hackathon)
python robot_sim.py

# Continuous random mode
python robot_sim.py continuous
```

---

## API Reference

### `POST /evaluate`
Submit a proposed robot action for safety evaluation.

**Request:**
```json
{
  "action_type": "MOVE_FORWARD",
  "parameters": { "speed": 1.5, "distance_m": 2.0 },
  "agent_id": "robot_01"
}
```

**Response:**
```json
{
  "request_id": "a1b2c3d4",
  "verdict": "BLOCK",
  "risk_score": 0.95,
  "reasoning": "Human detected at NEAR range...",
  "llm_explanation": "The forward movement has been blocked...",
  "violations": [
    {
      "rule_id": "HUMAN_PROXIMITY_CRITICAL",
      "severity": "critical",
      "description": "Human at NEAR range — collision risk"
    }
  ],
  "recommended_alternative": "STOP and wait for humans to clear",
  "scene_summary": {
    "human_count": 1,
    "obstacle_count": 0,
    "nearest_human": "near"
  }
}
```

### `GET /scene` — Latest scene snapshot
### `GET /history?limit=20` — Decision history
### `GET /health` — System status
### `WS  /ws` — Real-time WebSocket stream

---

## Safety Rules

| Rule ID | Trigger | Severity | Action |
|---|---|---|---|
| HUMAN_PROXIMITY_CRITICAL | Human at NEAR range + motion | critical | BLOCK |
| HUMAN_PROXIMITY_WARNING | Human at MID range + motion | warning | WARN |
| CROWDED_SCENE | 2+ humans + any motion | warning | WARN |
| EXCESSIVE_SPEED_HUMAN_PRESENT | Speed > 1.5m/s + human | critical | BLOCK |
| EXCESSIVE_SPEED | Speed > 2.5m/s | warning | WARN |
| GRIPPER_HUMAN_NEAR | Gripper close + human near | critical | BLOCK |
| ARM_EXTEND_OBSTRUCTED | Arm extend + human/obstacles | critical/warning | BLOCK/WARN |
| SPEED_INCREASE_BLOCKED | Speed++ + occupied scene | critical/warning | BLOCK/WARN |

---

## Vision Modes

- **Live mode**: Webcam + YOLOv8n inference (~30ms/frame)
- **Simulation mode**: Procedural scene generation (no camera needed)

Auto-detected at startup. Falls back to simulation if no camera or YOLO unavailable.

---

## File Structure

```
safeguard_sentinel/
├── api.py              # FastAPI backend (main intercept layer)
├── vision_module.py    # YOLOv8 + OpenCV + simulation
├── safety_engine.py    # Rule-based safety policy engine
├── llm_reasoner.py     # Claude API reasoning layer
├── dashboard.py        # Streamlit monitoring UI
├── robot_sim.py        # Demo robot agent simulator
├── requirements.txt
└── README.md
```

---

## Hackathon Demo Script

1. **Start the API** → `uvicorn api:app --port 8000`
2. **Open dashboard** → `streamlit run dashboard.py` → browser auto-opens
3. **Run structured demo** → `python robot_sim.py` (shows ALLOW → WARN → BLOCK pipeline)
4. **Switch to continuous mode** → `python robot_sim.py continuous`
5. **Enable "Auto-Simulation"** in dashboard sidebar for live updates
6. **Key talking points:**
   - Vision module detects humans in real-time (or simulation)
   - 8 safety rules evaluate every action before execution
   - LLM generates human-readable explanations
   - Dashboard shows live risk scores, violations, history
   - Zero latency for STOP commands (always ALLOW)
