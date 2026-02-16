"""
FRIDAY Voice Assistant Server
A FastAPI-based voice assistant with WebSocket support for real-time status updates.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pyttsx3
import os
import webbrowser
import threading
import psutil
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Callable, Any
import logging

try:
    import pyautogui
except ImportError:
    pyautogui = None
    logging.warning("pyautogui not installed - screenshot feature will be disabled")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="FRIDAY Voice Assistant",
    description="Voice-controlled assistant with system control capabilities",
    version="1.0.0"
)

# ============================================================================
# CORS Configuration
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# System State Management
# ============================================================================

class SystemState:
    """Manages the current state of the FRIDAY system."""
    
    def __init__(self):
        self.is_powered_on: bool = True
        self.is_speaking: bool = False
        self.is_mic_on: bool = True
        self.is_volume_on: bool = True
        self.last_command: str = ""
        self.awake: bool = False
        self.awake_until: datetime = None  # Timestamp when FRIDAY should go back to sleep
        self.start_time: datetime = datetime.now()
        self.awake_duration: int = 30  # Stay awake for 30 seconds
        self.speak_func = None  # Will be set after speak() is defined
    
    def is_awake(self) -> bool:
        """Check if FRIDAY is currently awake (within timeout period)."""
        if not self.awake:
            return False
        
        if self.awake_until and datetime.now() > self.awake_until:
            self.awake = False
            self.awake_until = None
            logger.info("FRIDAY went back to sleep (timeout)")
            # ✅ Speak when going to sleep
            if self.speak_func:
                self.speak_func("Sleep mode activated, sir. Say Friday to wake me.")
            return False
        
        return True
    
    def wake_up(self) -> None:
        """Wake up FRIDAY and set timeout."""
        self.awake = True
        self.awake_until = datetime.now() + timedelta(seconds=self.awake_duration)
        logger.info(f"FRIDAY is awake for {self.awake_duration} seconds")
    
    def extend_awake(self) -> None:
        """Extend the awake period when a command is executed."""
        if self.awake:
            self.awake_until = datetime.now() + timedelta(seconds=self.awake_duration)
    
    def sleep_now(self) -> None:
        """Put FRIDAY to sleep immediately."""
        self.awake = False
        self.awake_until = None
        logger.info("FRIDAY went to sleep")
    
    def reset(self):
        """Reset the system state to defaults."""
        self.is_powered_on = True
        self.is_speaking = False
        self.is_mic_on = True
        self.is_volume_on = True
        self.last_command = ""
        self.awake = False

# Global state instance
state = SystemState()

# ============================================================================
# Duplicate Command Prevention
# ============================================================================

class CommandDeduplicator:
    """Prevents duplicate commands from being executed within a short time window."""
    
    def __init__(self):
        self.last_command: str = ""
        self.last_command_time: float = 0.0
        self.duplicate_window: float = 5.0  # ✅ 5 seconds
    
    def is_duplicate(self, command: str) -> bool:
        """Check if this command is a duplicate of the recent one."""
        import time
        current_time = time.time()
        
        # Check if same command within time window
        if (command == self.last_command and 
            current_time - self.last_command_time < self.duplicate_window):
            logger.info(f"⏭️ Duplicate command blocked: '{command}' (within {self.duplicate_window}s)")
            return True
        
        # Update last command
        self.last_command = command
        self.last_command_time = current_time
        return False

# Global deduplicator instance
deduplicator = CommandDeduplicator()

# ============================================================================
# Pydantic Models
# ============================================================================

class PowerToggle(BaseModel):
    """Model for power toggle requests."""
    state: bool

class MicToggle(BaseModel):
    """Model for microphone toggle requests."""
    state: bool

class VolumeToggle(BaseModel):
    """Model for volume toggle requests."""
    state: bool

class SpeakRequest(BaseModel):
    """Model for text-to-speech requests."""
    text: str

class Command(BaseModel):
    """Model for voice command requests."""
    text: str

class StatusResponse(BaseModel):
    """Model for status response."""
    isPoweredOn: bool
    isSpeaking: bool
    isMicOn: bool
    isVolumeOn: bool
    lastCommand: str
    awake: bool
    stats: Dict[str, Any]

# ============================================================================
# Text-to-Speech Function
# ============================================================================

def speak(text: str) -> None:
    """
    Convert text to speech using pyttsx3.
    
    Args:
        text: The text to speak
    """
    if not state.is_powered_on or not state.is_volume_on:
        logger.info(f"[SPEAK] Muted/Offline - Message: {text}")
        return
    
    def run_tts():
        """Run TTS in a separate thread."""
        state.is_speaking = True
        logger.info(f"[FRIDAY]: {text}")
        
        try:
            engine = pyttsx3.init("sapi5")
            engine.setProperty("rate", 170)
            voices = engine.getProperty("voices")
            
            # Use female voice if available
            if len(voices) > 1:
                engine.setProperty("voice", voices[1].id)
            
            engine.say(text)
            engine.runAndWait()
            engine.stop()
            
        except Exception as e:
            logger.error(f"TTS Error: {e}")
        
        finally:
            state.is_speaking = False
    
    # Run TTS in a separate thread to avoid blocking
    threading.Thread(target=run_tts, daemon=True).start()

# ✅ Set speak function reference in state
state.speak_func = speak

# ============================================================================
# System Statistics
# ============================================================================

def get_system_stats() -> Dict[str, Any]:
    """
    Retrieve current system statistics.
    
    Returns:
        Dictionary containing battery, CPU, temperature, connectivity, and uptime
    """
    try:
        # Calculate uptime
        uptime = datetime.now() - state.start_time
        hours = int(uptime.total_seconds() // 3600)
        minutes = int((uptime.total_seconds() % 3600) // 60)
        
        # Get battery info
        battery_info = psutil.sensors_battery()
        battery = battery_info.percent if battery_info else 100
        
        # Get CPU usage
        cpu = psutil.cpu_percent(interval=0.1)
        
        return {
            "battery": round(battery, 1),
            "temperature": round(cpu, 1),  # Using CPU as temperature proxy
            "cpu": round(cpu, 1),
            "connectivity": "Strong",
            "uptime": f"{hours}h {minutes}m",
        }
    
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        return {
            "battery": 0,
            "temperature": 0,
            "cpu": 0,
            "connectivity": "Unknown",
            "uptime": "0h 0m",
        }

# ============================================================================
# Command Execution
# ============================================================================

def open_browser():
    """Open the default web browser to Google."""
    speak("Opening browser")
    webbrowser.open("https://google.com")

def open_google():
    """Open Google."""
    speak("Opening Google")
    webbrowser.open("https://google.com")

def open_youtube():
    """Open YouTube in the default browser."""
    speak("Opening YouTube")
    webbrowser.open("https://youtube.com")

def open_facebook():
    """Open Facebook in the default browser."""
    speak("Opening Facebook")
    webbrowser.open("https://facebook.com")

def open_vscode():
    """Open Visual Studio Code."""
    speak("Opening VS Code")
    os.system("code")

def open_notepad():
    """Open Notepad."""
    speak("Opening Notepad")
    os.system("start notepad")

def open_chatgpt():
    """Open ChatGPT app via Windows search."""
    speak("Opening ChatGPT")
    
    # Method 1: PyAutoGUI keyboard simulation (most reliable)
    if pyautogui:
        try:
            import time
            # Press Windows key
            pyautogui.press('win')
            time.sleep(0.5)
            # Type 'chatgpt'
            pyautogui.write('chatgpt', interval=0.1)
            time.sleep(0.5)
            # Press Enter
            pyautogui.press('enter')
            return
        except Exception as e:
            logger.error(f"PyAutoGUI ChatGPT launch failed: {e}")
    
    # Method 2: Fallback to web version
    try:
        webbrowser.open("https://chat.openai.com")
    except Exception as e:
        logger.error(f"ChatGPT web fallback failed: {e}")

def open_spotify():
    """Open Spotify."""
    speak("Opening Spotify")
    webbrowser.open("https://open.spotify.com")

def open_gmail():
    """Open Gmail."""
    speak("Opening Gmail")
    webbrowser.open("https://mail.google.com")

def open_github():
    """Open GitHub."""
    speak("Opening GitHub")
    webbrowser.open("https://github.com")

def open_calculator():
    """Open Windows Calculator."""
    speak("Opening Calculator")
    os.system("calc")

def open_cmd():
    """Open Command Prompt."""
    speak("Opening Command Prompt")
    os.system("start cmd")

def open_task_manager():
    """Open Task Manager."""
    speak("Opening Task Manager")
    os.system("taskmgr")

def open_settings():
    """Open Windows Settings."""
    speak("Opening Settings")
    os.system("start ms-settings:")

def open_file_explorer():
    """Open File Explorer."""
    speak("Opening File Explorer")
    os.system("explorer")

def open_paint():
    """Open Microsoft Paint."""
    speak("Opening Paint")
    os.system("mspaint")

def open_netflix():
    """Open Netflix."""
    speak("Opening Netflix")
    webbrowser.open("https://www.netflix.com")

def open_twitter():
    """Open Twitter/X."""
    speak("Opening Twitter")
    webbrowser.open("https://twitter.com")

def open_instagram():
    """Open Instagram."""
    speak("Opening Instagram")
    webbrowser.open("https://www.instagram.com")

def open_linkedin():
    """Open LinkedIn."""
    speak("Opening LinkedIn")
    webbrowser.open("https://www.linkedin.com")

def open_reddit():
    """Open Reddit."""
    speak("Opening Reddit")
    webbrowser.open("https://www.reddit.com")

def get_time():
    """Tell the current time."""
    current_time = datetime.now().strftime("%I:%M %p")
    speak(f"The time is {current_time}")

def get_date():
    """Tell the current date."""
    current_date = datetime.now().strftime("%B %d, %Y")
    speak(f"Today is {current_date}")

def lock_system():
    """Lock the computer."""
    speak("Locking the system")
    os.system("rundll32.exe user32.dll,LockWorkStation")

def sleep_system():
    """Put the computer to sleep."""
    speak("Putting the system to sleep")
    os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")

def restart_system():
    """Restart the computer."""
    speak("Understood, sir. Initiating system restart. I'll be back online shortly.")
    import time
    time.sleep(3)  # Give time for speech
    os.system("shutdown /r /t 1")

def shutdown_system():
    """Shutdown the system."""
    speak("I understand, sir. Initiating system shutdown sequence. It has been an honor serving you today. Goodbye.")
    import time
    time.sleep(4)  # Give time for speech to complete
    os.system("shutdown /s /t 1")

def increase_volume():
    """Increase system volume."""
    speak("Increasing volume")
    # Using nircmd (needs to be installed) or powershell
    os.system("powershell -c \"(New-Object -ComObject WScript.Shell).SendKeys([char]175)\"")

def decrease_volume():
    """Decrease system volume."""
    speak("Decreasing volume")
    os.system("powershell -c \"(New-Object -ComObject WScript.Shell).SendKeys([char]174)\"")

def mute_volume():
    """Mute/unmute system volume."""
    speak("Toggling mute")
    os.system("powershell -c \"(New-Object -ComObject WScript.Shell).SendKeys([char]173)\"")

def minimize_all():
    """Minimize all windows."""
    speak("Minimizing all windows")
    os.system("powershell -c \"(New-Object -ComObject Shell.Application).MinimizeAll()\"")

def take_screenshot():
    """Take a screenshot."""
    speak("Taking screenshot")
    try:
        import pyautogui
        screenshot_name = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        screenshot_path = os.path.join(os.path.expanduser("~"), "Pictures", screenshot_name)
        pyautogui.screenshot(screenshot_path)
        speak(f"Screenshot saved to Pictures folder")
    except Exception as e:
        logger.error(f"Screenshot error: {e}")
        speak("Sorry, I couldn't take a screenshot")

def show_help():
    """Tell the user what commands are available."""
    speak("I can help you with opening applications like browser, youtube, facebook, chatgpt, spotify, gmail, and more. I can also control your system with commands like lock, sleep, restart, or shutdown. I can tell you the time and date, take screenshots, and manage volume. For a full list, please check the documentation.")
    logger.info("Help command executed - listing available commands")

def list_commands():
    """List all available commands."""
    total_commands = len(COMMANDS)
    speak(f"I currently support {total_commands} different commands, sir. I can open applications, control your system, manage volume, and more. What would you like me to do?")
    logger.info(f"Listed {total_commands} available commands")

def greet_morning():
    """Morning greeting."""
    speak("Good morning sir. How may I assist you today?")

def greet_afternoon():
    """Afternoon greeting."""
    speak("Good afternoon sir. How may I help you?")

def greet_evening():
    """Evening greeting."""
    speak("Good evening sir. What can I do for you?")

def respond_thank_you():
    """Respond to thank you."""
    speak("You're welcome sir. Happy to help.")

def respond_how_are_you():
    """Respond to how are you."""
    speak("I'm functioning at optimal capacity, sir. All systems operational. How may I assist you?")

def shutdown_friday():
    """Shutdown FRIDAY backend server completely."""
    speak("Shutting down all FRIDAY systems, sir. Backend services terminating. Goodbye.")
    import time
    time.sleep(4)
    logger.info("FRIDAY backend shutdown initiated by user command")
    # Shutdown the FastAPI server
    os._exit(0)

# Command registry
COMMANDS: Dict[str, Callable] = {
    # Web browsers & apps
    "open browser": open_browser,
    "open google": open_google,
    "open youtube": open_youtube,
    "open facebook": open_facebook,
    "open chatgpt": open_chatgpt,
    "open spotify": open_spotify,
    "open gmail": open_gmail,
    "open github": open_github,
    "open netflix": open_netflix,
    "open twitter": open_twitter,
    "open instagram": open_instagram,
    "open linkedin": open_linkedin,
    "open reddit": open_reddit,
    
    # Desktop applications
    "open vscode": open_vscode,
    "open notepad": open_notepad,
    "open calculator": open_calculator,
    "open cmd": open_cmd,
    "open command prompt": open_cmd,
    "open task manager": open_task_manager,
    "open settings": open_settings,
    "open file explorer": open_file_explorer,
    "open explorer": open_file_explorer,
    "open paint": open_paint,
    
    # System information
    "what time": get_time,
    "time": get_time,
    "what date": get_date,
    "date": get_date,
    
    # System control
    "lock": lock_system,
    "lock system": lock_system,
    "sleep": sleep_system,
    "restart": restart_system,
    "shutdown": shutdown_system,
    
    # Volume control
    "increase volume": increase_volume,
    "volume up": increase_volume,
    "decrease volume": decrease_volume,
    "volume down": decrease_volume,
    "mute": mute_volume,
    "unmute": mute_volume,
    
    # Window management
    "minimize all": minimize_all,
    "minimize everything": minimize_all,
    "show desktop": minimize_all,
    
    # Screenshot
    "screenshot": take_screenshot,
    "take screenshot": take_screenshot,
    
    # Help & Info
    "help": show_help,
    "help me": show_help,
    "what can you do": show_help,
    "commands": list_commands,
    "list commands": list_commands,
    
    # Greetings & Courtesy
    "good morning": greet_morning,
    "good afternoon": greet_afternoon,
    "good evening": greet_evening,
    "thank you": respond_thank_you,
    "thanks": respond_thank_you,
    "how are you": respond_how_are_you,
    
    # Backend control (complete shutdown)
    "shutdown friday": shutdown_friday,
    "terminate friday": shutdown_friday,
    "kill server": shutdown_friday,
}

def execute_command(command_text: str) -> bool:
    """
    Execute a command based on the input text.
    
    Args:
        command_text: The command text to process
        
    Returns:
        True if a command was executed, False otherwise
    """
    logger.info(f"[COMMAND]: {command_text}")
    state.last_command = command_text
    
    command_lower = command_text.lower()
    
    # Check if any command keyword matches
    for keyword, action in COMMANDS.items():
        if keyword in command_lower:
            try:
                # Execute command in a separate thread
                threading.Thread(target=action, daemon=True).start()
                return True
            except Exception as e:
                logger.error(f"Error executing command '{keyword}': {e}")
                speak("Sorry sir, I encountered an error executing that command")
                return False
    
    # No command matched - give helpful feedback
    logger.info("No command matched")
    
    # Give intelligent response based on what they tried to do
    if "open" in command_lower:
        app_name = command_lower.replace("open", "").strip()
        speak(f"I'm sorry sir, I don't have the ability to open {app_name} yet. That feature is still in training.")
    elif "play" in command_lower:
        speak("I'm sorry sir, I don't support music playback yet. That feature is still in training.")
    elif "search" in command_lower or "find" in command_lower:
        speak("I'm sorry sir, I don't have search capabilities yet. That feature is still in training.")
    elif "call" in command_lower or "dial" in command_lower:
        speak("I'm sorry sir, I cannot make calls yet. That feature is still in training.")
    elif "send" in command_lower or "message" in command_lower:
        speak("I'm sorry sir, I cannot send messages yet. That feature is still in training.")
    elif "tell me" in command_lower or "what is" in command_lower or "what are" in command_lower:
        speak("I'm sorry sir, I don't have general knowledge capabilities yet. That feature is still in training.")
    else:
        speak("I'm sorry sir, I didn't understand that command. That feature may not be available yet or is still in training.")
    
    return False

# ============================================================================
# API Routes
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "message": "FRIDAY Voice Assistant is running",
        "version": "1.0.0",
        "status": "operational"
    }

@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    """Get the current system status."""
    return {
        "isPoweredOn": state.is_powered_on,
        "isSpeaking": state.is_speaking,
        "isMicOn": state.is_mic_on,
        "isVolumeOn": state.is_volume_on,
        "lastCommand": state.last_command,
        "awake": state.is_awake(),
        "stats": get_system_stats(),
    }

@app.post("/api/power")
async def toggle_power(data: PowerToggle):
    """Toggle the power state of the system."""
    # If turning off, say goodbye first
    if not data.state and state.is_powered_on:
        speak("Going offline, sir. It's been a pleasure serving you today. Systems powering down now.")
        # Give time for speech to complete
        await asyncio.sleep(3)
    
    state.is_powered_on = data.state
    logger.info(f"Power toggled: {data.state}")
    
    # If turning back on, greet
    if data.state and not state.is_powered_on:
        speak("Systems online. FRIDAY at your service, sir.")
    
    return {"success": True, "isPoweredOn": state.is_powered_on}

@app.post("/api/mic")
async def toggle_mic(data: MicToggle):
    """Toggle the microphone state."""
    state.is_mic_on = data.state
    logger.info(f"Microphone toggled: {data.state}")
    return {"success": True, "isMicOn": state.is_mic_on}

@app.post("/api/volume")
async def toggle_volume(data: VolumeToggle):
    """Toggle the volume state."""
    state.is_volume_on = data.state
    logger.info(f"Volume toggled: {data.state}")
    return {"success": True, "isVolumeOn": state.is_volume_on}

@app.post("/api/speak")
async def speak_text(data: SpeakRequest):
    """Make FRIDAY speak the provided text."""
    if not data.text.strip():
        return {"success": False, "error": "Empty text provided"}
    
    speak(data.text)
    return {"success": True, "text": data.text}

@app.post("/api/command")
async def receive_command(data: Command):
    """
    Receive and process voice commands from the phone/client.
    
    The wake word "friday" must be spoken to activate the assistant.
    FRIDAY stays awake for 30 seconds after wake word or last command.
    """
    command = data.text.lower().strip()
    logger.info(f"🎤 Command received: {command}")
    
    if not command:
        return {"success": False, "error": "Empty command"}
    
    # ✅ Check for duplicate commands (prevents rapid-fire duplicates)
    if deduplicator.is_duplicate(command):
        return {
            "success": True,
            "duplicate": True,
            "message": "Duplicate command ignored"
        }
    
    # Check for wake word
    if "friday" in command:
        state.wake_up()
        speak("Good Day sir , Pleasure to serve on your service. How may I assist you today?")
        return {
            "success": True,
            "wake": True,
            "message": "Wake word detected",
            "awake_until": state.awake_until.isoformat() if state.awake_until else None
        }
    
    # Check for sleep command
    if "sleep" in command or "go to sleep" in command or "goodbye friday" in command:
        if state.is_awake():
            state.sleep_now()
            speak("Of course, sir. Going into sleep mode. I'll be here when you need me.")
            return {
                "success": True,
                "sleep": True,
                "message": "FRIDAY is going to sleep"
            }
    
    # Execute command if awake
    if state.is_awake():
        executed = execute_command(command)
        
        # Extend awake time after successful command
        if executed:
            state.extend_awake()
        
        return {
            "success": True,
            "executed": executed,
            "message": "Command executed" if executed else "No matching command",
            "awake_until": state.awake_until.isoformat() if state.awake_until else None
        }
    
    return {
        "success": True,
        "message": "Waiting for wake word ('Friday')"
    }

# ============================================================================
# WebSocket for Real-time Updates
# ============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time status updates.
    Sends system status updates every second.
    """
    await websocket.accept()
    logger.info("WebSocket client connected")
    
    try:
        while True:
            # Send current status
            await websocket.send_json({
                "isPoweredOn": state.is_powered_on,
                "isSpeaking": state.is_speaking,
                "isMicOn": state.is_mic_on,
                "isVolumeOn": state.is_volume_on,
                "lastCommand": state.last_command,
                "awake": state.is_awake(),
                "awakeUntil": state.awake_until.isoformat() if state.awake_until else None,
                "stats": get_system_stats(),
            })
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")

# ============================================================================
# Startup and Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup."""
    logger.info("FRIDAY Voice Assistant starting up...")
    logger.info("System ready to receive commands")
    
    # FRIDAY-style startup message (will speak when first command received)
    # Note: Don't speak here as TTS might not be ready yet

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    logger.info("FRIDAY Voice Assistant shutting down...")
    speak("System shutdown initiated. It's been a pleasure, sir.")
    await asyncio.sleep(2)

# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting FRIDAY Voice Assistant Server...")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )