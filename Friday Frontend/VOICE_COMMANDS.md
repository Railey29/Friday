# Voice Command Implementation Guide

## 🎤 Voice Commands Overview

Your `/api/listen` endpoint needs to implement actual voice recognition that can understand user commands.

## 📝 Supported Command Examples

These are examples of voice commands your system should understand:

```
User Says → Backend Should Return
─────────────────────────────────

"Increase volume" → {"command": "increase_volume", "level": 50}
"Increase volume to 80%" → {"command": "set_volume", "level": 80}
"Decrease volume" → {"command": "decrease_volume", "level": 30}
"Turn on mic" → {"command": "toggle_mic", "state": true}
"Turn off mic" → {"command": "toggle_mic", "state": false}
"Shutdown" → {"command": "power_off"}
"Turn on" → {"command": "power_on"}
"What's your status?" → {"command": "status"}
"Speak this message" → {"command": "speak", "text": "..."}
```

## 🛠️ Backend Implementation Example

### FastAPI Implementation

```python
from fastapi import FastAPI
import speech_recognition as sr
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize speech recognizer
recognizer = sr.Recognizer()

@app.post("/api/listen")
async def listen():
    """
    Record audio and recognize voice commands
    """
    try:
        with sr.Microphone() as source:
            print("Listening for command...")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            audio = recognizer.listen(source, timeout=5)
        
        # Use Google Speech Recognition (free, requires internet)
        command = recognizer.recognize_google(audio).lower()
        print(f"Recognized: {command}")
        
        # Parse command
        result = parse_voice_command(command)
        
        return {
            "success": True,
            "command": command,
            "parsed": result
        }
    
    except sr.UnknownValueError:
        return {
            "success": False,
            "error": "Could not understand audio",
            "command": None
        }
    except sr.RequestError as e:
        return {
            "success": False,
            "error": f"Speech recognition service error: {e}",
            "command": None
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "command": None
        }

def parse_voice_command(command: str) -> dict:
    """
    Parse voice command and extract intent
    """
    command = command.lower().strip()
    
    # Increase volume
    if "increase volume" in command or "turn volume up" in command:
        if "to" in command and "%" in command:
            # Extract percentage: "increase volume to 80%"
            parts = command.split("to")
            level_str = parts[-1].replace("%", "").strip()
            try:
                level = int(level_str)
                return {"action": "set_volume", "level": min(100, max(0, level))}
            except:
                return {"action": "increase_volume", "amount": 10}
        return {"action": "increase_volume", "amount": 10}
    
    # Decrease volume
    if "decrease volume" in command or "turn volume down" in command:
        return {"action": "decrease_volume", "amount": 10}
    
    # Power commands
    if "turn on" in command or "power on" in command:
        return {"action": "power_on"}
    if "turn off" in command or "shutdown" in command or "power off" in command:
        return {"action": "power_off"}
    
    # Mic commands
    if "turn on mic" in command or "enable mic" in command:
        return {"action": "enable_mic"}
    if "turn off mic" in command or "disable mic" in command:
        return {"action": "disable_mic"}
    
    # Status
    if "status" in command or "how are you" in command:
        return {"action": "status"}
    
    # Unknown
    return {"action": "unknown", "original": command}
```

### Installation

```bash
# Install required packages
pip install SpeechRecognition pyaudio

# On Linux (if pyaudio fails):
sudo apt-get install portaudio19-dev
pip install pyaudio

# On Windows (using conda):
conda install pyaudio

# Optional: For cloud speech recognition
pip install google-cloud-speech
```

## 🔊 Test Your Voice Recognition

```bash
# Simple test script
python -c "
import speech_recognition as sr
r = sr.Recognizer()
with sr.Microphone() as source:
    print('Say something!')
    audio = r.listen(source)
    try:
        text = r.recognize_google(audio)
        print(f'You said: {text}')
    except:
        print('Could not understand')
"
```

## 📊 Response Format

Your `/api/listen` should return:

```json
{
  "success": true,
  "command": "increase volume to 80%",
  "parsed": {
    "action": "set_volume",
    "level": 80
  }
}
```

Or if it failed:

```json
{
  "success": false,
  "error": "Could not understand audio",
  "command": null
}
```

## 🔄 Frontend Update Flow

When user clicks "Listen":

1. Frontend → `POST /api/listen`
2. Backend records audio (5 seconds)
3. Backend processes with speech-to-text
4. Backend returns recognized command
5. Frontend shows: `"Last Command: increase volume to 80%"`
6. Backend executes the command

## 🚀 Quick Start (Minimal Implementation)

```python
# Simplest working example
from fastapi import FastAPI
import speech_recognition as sr

app = FastAPI()

@app.post("/api/listen")
async def listen():
    recognizer = sr.Recognizer()
    
    try:
        with sr.Microphone() as source:
            audio = recognizer.listen(source, timeout=5)
        command = recognizer.recognize_google(audio)
        return {"success": True, "command": command}
    except:
        return {"success": False, "command": None}
```

## ✅ Make Your Backend Say Commands

Update your `POST /api/speak` endpoint:

```python
import pyttsx3

@app.post("/api/speak")
async def speak(text: str):
    """Speak the provided text"""
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()
    
    return {"success": True, "text": text}
```

## 🎯 Next Steps

1. ✅ Install speech recognition libraries
2. ✅ Implement `/api/listen` with voice recognition
3. ✅ Add command parsing logic
4. ✅ Test voice commands in frontend
5. ✅ Implement `/api/speak` for text-to-speech
6. ✅ Handle errors gracefully

**Your frontend is ready to receive voice commands!** 🎉
