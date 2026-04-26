# g1_vision_conductor
AI-driven music conductor agent for Unitree G1 using Parallel Perception (Music 4D)
# 🤖 G1 Maestro: Multimodal AI Music Conductor

This project transforms the **Unitree G1 Humanoid Robot** into an intelligent music conductor. Using a "Music 4D" parallel perception architecture, the G1 can see sheet music, track beats in real-time, and analyze audience emotion.

---

## 🏛️ Architecture: Sequential vs. Parallel (Music 4D)

To achieve the rhythm required for a 120 BPM tempo, this project utilizes a **Parallel Fan-Out** architecture to reduce latency from ~108ms to ~68ms.

![Architecture Diagram](./IMG-20260426-WA0026.jpg)

---

## 🛠️ Hardware Stack
* **Unitree G1:** Onboard Jetson Orin (Edge Perception).
* **GPU Workstation:** NVIDIA RTX A4500 (Remote Brain) running **Ollama**.

---

## 🚀 Quick Start

1.  **Workstation:** `OLLAMA_HOST="0.0.0.0" ollama serve`
2.  **G1 (Bridge):** `./g1_vision_server eth0`
3.  **G1 (Agent):** `conda activate g1_ai && python agent.py`

---

## 📅 Project Status
- [x] C++ Vision Server Bridge
- [x] External GPU Offloading (Ollama)
- [x] Sequential VAD/STT Pipeline
- [ ] Async Parallel Perception Loop (In Progress)
- [ ] Gesture Synthesis Engine
