# QUICK FIX: Backend Connection Issue

## 🔴 Your Problem
- Frontend: VS Code Dev Container (Linux)
- Backend: Windows PC running on `localhost:8000`
- Frontend can't communicate with backend

## ✅ The Fix (Already Applied!)

### 1. Environment Updated
Your `.env.local` now has:
```bash
NEXT_PUBLIC_API_URL=http://host.docker.internal:8000
NEXT_PUBLIC_USE_MOCK_API=false
```

### 2. What Changed
- ✅ API URL points to `host.docker.internal` (bridges container to Windows PC)
- ✅ Mock API disabled (now uses your real backend)
- ✅ Enhanced error messages for network debugging

### 3. What You Need To Do

#### Step A: Start Your Backend (if not already running)
```bash
PS C:\Users\HomePC\Downloads\Friday> uvicorn Friday:app --host 0.0.0.0 --port 8000
INFO:     Started server process [20656]
INFO:     Uvicorn running on http://0.0.0.0:8000
```

#### Step B: Add CORS to Your FastAPI Backend
Open your `Friday/app.py` and add this at the top:

```python
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rest of your code...
```

#### Step C: Reload Frontend (Hard Refresh)
- Press **Ctrl+Shift+R** (Windows/Linux)
- Or **Cmd+Shift+R** (Mac)

#### Step D: Check Browser Console (F12)
You should see:
```
[🤖 Robot Service] Initialized with:
   API URL: http://host.docker.internal:8000
   Mock API: ❌ Disabled (Production)

[🌐 Network Diagnostics]
Environment: Container
Suggested API URL: http://host.docker.internal:8000
```

## 🎤 Voice Command Issue

The "Increase volume to 80%" you saw was **mock data**. Your real backend needs to implement actual voice recognition.

### Update Your `/api/listen` Endpoint

Add voice recognition to your backend:

```python
import speech_recognition as sr

@app.post("/api/listen")
async def listen():
    """Listen for voice commands"""
    recognizer = sr.Recognizer()
    
    try:
        with sr.Microphone() as source:
            print("🎤 Listening...")
            audio = recognizer.listen(source, timeout=5)
        
        # Use Google Speech Recognition
        command = recognizer.recognize_google(audio).lower()
        print(f"✅ Recognized: {command}")
        
        return {
            "success": True,
            "command": command,
            "lastCommand": command
        }
    
    except sr.UnknownValueError:
        return {"success": False, "error": "Could not understand"}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### Install Libraries
```bash
pip install SpeechRecognition pyaudio
```

## ✅ Verification Checklist

- [ ] Backend running: `uvicorn Friday:app --host 0.0.0.0 --port 8000`
- [ ] CORS middleware added to FastAPI
- [ ] `.env.local` has `NEXT_PUBLIC_API_URL=http://host.docker.internal:8000`
- [ ] Frontend reloaded (Ctrl+Shift+R)
- [ ] Browser console shows network diagnostics
- [ ] Voice recognition libraries installed (`pip install SpeechRecognition`)

## 🧪 Test Connection

### From Frontend Console (F12)
Click any button and check console for:
```
[API Request] POST http://host.docker.internal:8000/api/power
[API Response] 200 OK
```

### From Backend Terminal
You should see the request logged:
```
INFO:     127.0.0.1:xxxxx "POST /api/power HTTP/1.1" 200 OK
```

## ❌ Still Not Working?

### Issue 1: "Network error: Could not reach the server"
**Solution**: 
```bash
# Check if backend is running
curl http://localhost:8000/health

# If not running, start it:
uvicorn Friday:app --host 0.0.0.0 --port 8000
```

### Issue 2: Backend sees no requests
**Solution**: 
- CORS not enabled - add the middleware (see Step B above)
- Check `.env.local` has `NEXT_PUBLIC_API_URL=http://host.docker.internal:8000`
- Hard reload frontend (Ctrl+Shift+R)

### Issue 3: Voice commands still not recognized
**Solution**:
- Install `SpeechRecognition`: `pip install SpeechRecognition pyaudio`
- Test manually: `python -c "import speech_recognition; print('OK')"`
- Implement actual voice recognition in `/api/listen`

## 📚 Detailed Guides
- For network setup details: See `CONTAINER_NETWORKING.md`
- For voice command implementation: See `VOICE_COMMANDS.md`
- For backend setup: See `BACKEND_SETUP.md`

## 🚀 TL;DR

1. ✅ API URL fixed to `host.docker.internal:8000`
2. 🔧 Add CORS to your FastAPI backend
3. 🎤 Add voice recognition to `/api/listen`
4. 🔄 Reload frontend (Ctrl+Shift+R)
5. ✅ Done!

**Reload your frontend now!** 🎉
