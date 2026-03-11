# Container vs Backend Network Guide

## 🌐 Your Situation

- **Frontend**: Running in VS Code Dev Container (Linux)
- **Backend**: Running on Windows PC (`localhost:8000`)
- **Problem**: Container's `localhost` ≠ Windows PC's `localhost`

## ✅ Solution: Use `host.docker.internal`

Your `.env.local` is now set to:

```bash
NEXT_PUBLIC_API_URL=http://host.docker.internal:8000
```

This tells the container to reach **your Windows machine's localhost**.

### How It Works

```
┌─────────────────────┐
│  Dev Container      │
│  (Linux)            │
│                     │
│  Frontend (Next.js) │
│  NEXT_PUBLIC_API_URL│
│     ↓               │
│  host.docker.internal:8000
│     ↓               │
└─────────┬───────────┘
          │ (Docker bridge)
          ↓
┌─────────────────────┐
│  Your Windows PC    │
│                     │
│  Backend (FastAPI)  │
│  localhost:8000     │
└─────────────────────┘
```

## 🚀 Step-by-Step Setup

### 1. Verify Backend is Running
```bash
PS C:\Users\HomePC\Downloads\Friday> uvicorn Friday:app --host 0.0.0.0 --port 8000
```

✅ You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

### 2. Test Backend is Accessible
```bash
# From Windows PowerShell
curl http://localhost:8000/api/status

# From another machine (replace IP)
curl http://192.168.x.x:8000/api/status
```

### 3. Enable CORS on Backend
Your FastAPI backend needs to allow requests from the frontend:

```python
# In your Friday/app.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (for dev)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 4. Reload Frontend
```bash
# In VS Code = Ctrl+Shift+R (hard refresh)
# Or check browser DevTools → Console
```

### 5. Check Console Logs
Look for:
```
[🤖 Robot Service] Initialized with:
   API URL: http://host.docker.internal:8000
   Mock API: ❌ Disabled (Production)

[🌐 Network Diagnostics]
Environment: Container
Suggested API URL: http://host.docker.internal:8000
```

## 🎤 Voice Command Issue

The "Increase volume to 80%" output is from the **mock API** (hardcoded test data).

Your **real backend** needs to implement actual voice recognition.

### What Your Backend Needs

```python
@app.post("/api/listen")
async def listen():
    """
    Record audio and process voice commands
    Should return the recognized command
    """
    # 1. Record audio from microphone (async)
    # 2. Send to speech-to-text service (Google Cloud, Azure, etc.)
    # 3. Process the text command
    # 4. Execute the command
    # 5. Return the result
    
    return {
        "command": "increase volume to 80%",
        "success": True
    }
```

### Recommended Libraries for Voice
- **SpeechRecognition** - Python library for speech-to-text
- **PyAudio** - Audio capture
- **TensorFlow** - Voice command recognition
- **Google Cloud Speech-to-Text** - Cloud API

## 🔧 Alternative: Direct IP Address

If `host.docker.internal` doesn't work:

```bash
# Windows: Find your PC's IP
ipconfig

# Look for IPv4 Address, e.g., 192.168.1.100
# Update .env.local:
NEXT_PUBLIC_API_URL=http://192.168.1.100:8000
```

## ✅ Verification Checklist

- [ ] Backend running: `uvicorn Friday:app --host 0.0.0.0 --port 8000`
- [ ] CORS enabled in FastAPI
- [ ] `.env.local` has `NEXT_PUBLIC_API_URL=http://host.docker.internal:8000`
- [ ] Frontend reloaded (Ctrl+Shift+R)
- [ ] Console shows network diagnostics info
- [ ] Backend receives requests (check your backend terminal)
- [ ] Voice commands implemented in backend

## 🐛 Debugging

### Check Backend Received Request
Your backend terminal should show:
```
INFO:     127.0.0.1:12345 "POST /api/listen HTTP/1.1" 200 OK
```

### Check Frontend Error
Browser Console (F12):
```
[Debugging Checklist]
  1. Verify backend is running
  2. If backend on different machine:
     - Update NEXT_PUBLIC_API_URL
     - For container → host: http://host.docker.internal:8000
```

### Test Connection Manually
```bash
# From container terminal
curl http://host.docker.internal:8000/health

# Should return something like:
# {"status":"ok"}
```

## 🎉 Next Steps

1. ✅ Updated API URL to `host.docker.internal`
2. ✅ Reload your frontend
3. 🔄 Add CORS to your FastAPI backend
4. 🎤 Implement actual voice recognition in `/api/listen`
5. 🧪 Test button clicks - should now hit your real backend!

**Reload your page now!** 🚀
