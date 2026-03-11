<div align="center">

<img src="https://img.shields.io/badge/FRIDAY-Voice%20Assistant-blue?style=for-the-badge&logo=robot" alt="FRIDAY"/>

# 🤖 FRIDAY Voice Assistant

**A voice-controlled AI assistant with full system control capabilities**

*"Think of me as the voice in your corner, sir."*

<br/>

![Python](https://img.shields.io/badge/Python-3.8+-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?style=flat-square&logo=fastapi)
![Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-orange?style=flat-square&logo=google)
![TypeScript](https://img.shields.io/badge/TypeScript-Frontend-blue?style=flat-square&logo=typescript)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

</div>

---

## 📖 About

FRIDAY is a voice-controlled AI assistant powered by **Google Gemini 2.5 Flash**. It understands both **Filipino and English** commands, controls your Windows system, opens apps, manages volume/brightness, and holds natural conversations — just like a real AI assistant.

---

## 🗂️ Project Structure

```
Friday/
├── Friday Backend/       # FastAPI backend (REST API + WebSocket)
│   ├── app/
│   │   ├── controllers/  # API & WebSocket routes
│   │   ├── models/       # App state management
│   │   ├── services/     # Gemini AI, TTS, system actions
│   │   └── main.py       # FastAPI app entry point
│   ├── pyproject.toml
│   ├── requirements.txt
│   └── .env              # Your API keys (not committed)
│
└── Friday Frontend/      # Frontend UI
    └── src/
        └── config.ts     # ← Edit this for your IP address
```

---

## ✨ Features

- 🤖 **Gemini 2.5 Flash AI** — Natural language understanding
- 🎙️ **Text-to-Speech** — Responds with voice via `pyttsx3`
- 🔌 **WebSocket** — Real-time state updates every second
- 🌐 **REST API** — Full control via FastAPI endpoints
- 🇵🇭 **Bilingual** — Filipino & English commands
- 📊 **System Monitoring** — Live CPU, RAM, battery stats
- ⚙️ **System Control** — Open apps, volume, brightness, shutdown & more

---

## 🎮 Supported Commands

| Category | Examples |
|----------|---------|
| 🌐 Open websites | `buksan youtube`, `open github`, `open spotify` |
| 💻 Open apps | `open vs code`, `buksan notepad`, `open calculator` |
| 🔊 Volume | `volume up`, `i-mute`, `unmute` |
| 💡 Brightness | `brightness up`, `babaan brightness` |
| 📸 Screenshot | `screenshot`, `kumuha ng screenshot` |
| 🖥️ System | `shutdown`, `restart`, `lock screen`, `minimize all` |
| 📊 Stats | `anong oras na?`, `battery`, `cpu usage`, `ram usage` |
| 💬 Chat | `kamusta?`, `joke naman`, `sino ka?` |

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Railey29/Friday.git
cd Friday
```

### 2. Setup the Backend

```bash
cd "Friday Backend"
pip install -r requirements.txt
```

Create a `.env` file inside `Friday Backend/`:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```
Get your free Gemini API key at 👉 https://aistudio.google.com/apikey

Run the backend:
```bash
uvicorn app.main:app --reload
```

---

### 3. Setup the Frontend

Open this file:
```
Friday Frontend/src/config.ts
```

Update your IP address:
```typescript
export const BACKEND_URL = "http://YOUR_IP_HERE:8000";
export const API_URL = "http://YOUR_IP_HERE:8000/api";
```

> 💡 **Find your IP:** Open Command Prompt and run `ipconfig` — look for **IPv4 Address**

Then run the frontend:
```bash
cd "Friday Frontend"
npm install
npm run dev
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| GET | `/api/status` | Get current system status |
| POST | `/api/command` | Send a voice/text command |
| POST | `/api/power` | Toggle FRIDAY on/off |
| POST | `/api/mic` | Toggle microphone |
| POST | `/api/volume` | Toggle volume |
| POST | `/api/speak` | Trigger text-to-speech |
| WS | `/ws` | WebSocket for real-time updates |

---

## 📦 Install as pip package

```bash
pip install friday-assistant
```

---

## 📋 Requirements

- Python >= 3.8
- Windows OS (TTS and system controls)
- Node.js >= 16 (for frontend)
- Google Gemini API key

---

## 📄 License

MIT License — Created by [Railey29](https://github.com/Railey29)
