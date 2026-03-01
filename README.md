# SafeGuard Sentinel
### AI Governance Layer for Autonomous Robotics

> **Intercept · Evaluate · Govern**  
> Because autonomous systems should never act without oversight.

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green?style=flat-square)
![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-red?style=flat-square)
![Claude AI](https://img.shields.io/badge/Claude-Anthropic-orange?style=flat-square)
![Streamlit](https://img.shields.io/badge/Streamlit-1.33-pink?style=flat-square)

SafeGuard Sentinel is a real-time AI safety layer that sits between 
an autonomous robot and its actions. Every proposed action is 
intercepted, analyzed with computer vision, evaluated against safety 
policies, and either ALLOWED, WARNED, or BLOCKED — before a single 
motor turns.

## 🎯 The Problem
Autonomous robots act freely with no real-time oversight layer.
When accidents happen, there's no record of why. Humans are cut 
out of the loop entirely.

## ✅ Our Solution
SafeGuard Sentinel intercepts every action before execution:

Robot proposes action → Vision analyzes scene → Policy engine 
evaluates risk → LLM explains decision → ALLOW or BLOCK

## 🚀 Quick Start

​```bash
# 1. Install
pip install -r requirements.txt

# 2. Start API
uvicorn api:app --port 8000

# 3. Start Dashboard
streamlit run dashboard.py

# 4. Run Robot Simulator
python robot_sim.py
​```

## 🔑 Optional: LLM Explanations
​```bash
export ANTHROPIC_API_KEY=your_key_here
​```

## 📁 Project Structure

​```
safeguard_sentinel/
├── api.py              # FastAPI backend — main intercept layer
├── vision_module.py    # YOLOv8 + OpenCV detection
├── safety_engine.py    # 8-rule safety policy engine
├── llm_reasoner.py     # Claude AI explanation layer
├── zone_manager.py     # Spatial zone mapping
├── fleet_manager.py    # Multi-robot fleet tracking
├── override_manager.py # Human override + audit trail
├── dashboard.py        # Streamlit live dashboard
├── robot_sim.py        # Demo robot agent simulator
└── requirements.txt
​```

## 🛡️ Safety Rules

| Rule | Trigger | Verdict |
|------|---------|---------|
| HUMAN_PROXIMITY_CRITICAL | Human at NEAR range + motion | BLOCK |
| EXCESSIVE_SPEED_HUMAN_PRESENT | Speed >1.5m/s near human | BLOCK |
| GRIPPER_HUMAN_NEAR | Gripper close + human nearby | BLOCK |
| HUMAN_PROXIMITY_WARNING | Human at MID range | WARN |
| CROWDED_SCENE | 2+ humans detected | WARN |
| ARM_EXTEND_OBSTRUCTED | Arm extend + obstacles | WARN/BLOCK |
| SPEED_INCREASE_BLOCKED | Speed++ in occupied scene | WARN/BLOCK |

## ⚡ Key Features
- **Zone Mapping** — draw RESTRICTED/WARNING/SAFE zones on camera feed
- **Multi-Robot Fleet** — track multiple agents with fleet-level safety rules
- **Human Override** — operators challenge BLOCK decisions with full audit trail
- **LLM Explanations** — Claude AI explains every decision in plain English
- **Simulation Mode** — works without hardware, auto-detects webcam

## 🏗️ Built With
- Python · FastAPI · Streamlit · YOLOv8 · OpenCV
- Anthropic Claude API · WebSocket · Pydantic

## 📄 License
MIT
```

---

**GitHub Topics to add** (under the repo description):
```
robotics  ai-safety  computer-vision  yolov8  fastapi  
streamlit  autonomous-systems  human-in-the-loop  
python  anthropic  real-time  hackathon
