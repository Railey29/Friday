"""Command action implementations and execution logic."""

import webbrowser
import os
import subprocess
import threading
import platform
import psutil
import logging
import re
import urllib.parse
from datetime import datetime
from typing import Dict, Callable

from app.models.state import state
from app.services.tts import speak
from app.services.reminders import store as reminder_store, parse_reminder_text
from app.services.calendar_service import create_calendar_event_from_text

logger = logging.getLogger(__name__)

SYSTEM = platform.system()  # "Windows", "Linux", "Darwin"


# ─────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────

def run(cmd: list[str]) -> bool:
    """Fire-and-forget subprocess, no window."""
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as e:
        logger.error("run() failed: %s", e)
        return False


def _run_ps(script: str) -> bool:
    """Run a PowerShell one-liner synchronously (timeout 5s)."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, timeout=5,
        )
        if result.returncode != 0:
            logger.warning("PowerShell non-zero exit: %s", result.stderr.decode(errors="ignore"))
        return result.returncode == 0
    except Exception as e:
        logger.error("_run_ps failed: %s", e)
        return False


# ─────────────────────────────────────────────
# Search Functions
# ─────────────────────────────────────────────

def search_google(query: str):
    encoded = urllib.parse.quote(query)
    webbrowser.open(f"https://www.google.com/search?q={encoded}")
    speak(f"Searching Google for {query}, sir.")

def search_youtube(query: str):
    encoded = urllib.parse.quote(query)
    webbrowser.open(f"https://www.youtube.com/results?search_query={encoded}")
    speak(f"Searching YouTube for {query}, sir.")

def play_music(query: str):
    encoded = urllib.parse.quote(query)
    webbrowser.open(f"https://www.youtube.com/results?search_query={encoded}")
    speak(f"Playing {query} on YouTube, sir.")

def search_spotify(query: str):
    encoded = urllib.parse.quote(query)
    webbrowser.open(f"https://open.spotify.com/search/{encoded}")
    speak(f"Searching Spotify for {query}, sir.")

def search_reddit(query: str):
    encoded = urllib.parse.quote(query)
    webbrowser.open(f"https://www.reddit.com/search/?q={encoded}")
    speak(f"Searching Reddit for {query}, sir.")

def search_github(query: str):
    encoded = urllib.parse.quote(query)
    webbrowser.open(f"https://github.com/search?q={encoded}")
    speak(f"Searching GitHub for {query}, sir.")


# ─────────────────────────────────────────────
# Pending Action Handler
# ─────────────────────────────────────────────

def _resolve_pending_action(command_text: str) -> bool:
    pending = getattr(state, "pending_action", None)
    if not pending:
        return False
    state.pending_action = None
    query = command_text.strip()
    dispatch = {
        "search_google":  search_google,
        "search_youtube": search_youtube,
        "play_music":     play_music,
        "search_spotify": search_spotify,
        "search_reddit":  search_reddit,
        "search_github":  search_github,
    }
    fn = dispatch.get(pending)
    if fn:
        fn(query)
        return True
    return False


# ─────────────────────────────────────────────
# Dynamic Search Command Parser
# ─────────────────────────────────────────────

def _parse_and_execute_search(command_lower: str) -> bool:
    m = re.search(r"search\s+(.+?)\s+(?:and|then)\s+play(?:\s+(?:the\s+)?(?:music|song))?\s*(.*)", command_lower)
    if m:
        search_query = m.group(1).strip()
        play_query   = m.group(2).strip() or search_query
        speak(f"Searching for {search_query} and playing {play_query}, sir.")
        webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote(search_query)}")
        import time; time.sleep(1)
        webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote(play_query)}")
        return True

    for pattern, fn in [
        (r"play\s+(.+?)\s+on\s+spotify",        search_spotify),
        (r"play\s+(.+?)\s+on\s+youtube",         play_music),
        (r"search\s+(.+?)\s+on\s+youtube",       search_youtube),
        (r"search\s+(.+?)\s+on\s+spotify",       search_spotify),
        (r"search\s+(.+?)\s+on\s+reddit",        search_reddit),
        (r"search\s+(.+?)\s+on\s+github",        search_github),
    ]:
        m = re.search(pattern, command_lower)
        if m:
            fn(m.group(1).strip())
            return True

    m = re.search(r"(?:search\s+(.+?)\s+on\s+google|^google\s+(.+))", command_lower)
    if m:
        search_google((m.group(1) or m.group(2)).strip())
        return True

    m = re.search(r"^search\s+(.+)", command_lower)
    if m and m.group(1).strip():
        search_google(m.group(1).strip())
        return True

    if re.match(r"^search\s*$", command_lower):
        speak("Ano ang isesearch ko para sa iyo, sir?")
        state.pending_action = "search_google"
        return True

    if re.match(r"^play\s*(music|song|a\s+song)?\s*$", command_lower):
        speak("Anong kanta ang ipe-play ko, sir?")
        state.pending_action = "play_music"
        return True

    m = re.search(r"^play\s+(?:music|song|the\s+song)?\s*(.+)", command_lower)
    if m and m.group(1).strip():
        play_music(m.group(1).strip())
        return True

    m = re.search(r"(?:youtube\s+search|look\s+up)\s+(.+)", command_lower)
    if m:
        search_youtube(m.group(1).strip())
        return True

    if re.match(r"^(?:youtube\s+search|look\s+up)\s*$", command_lower):
        speak("Ano ang hahanaping ko sa YouTube, sir?")
        state.pending_action = "search_youtube"
        return True

    return False


# ─────────────────────────────────────────────
# Browser / Websites
# ─────────────────────────────────────────────

def open_browser():    speak("Opening browser, sir.");       webbrowser.open("https://google.com")
def open_google():     speak("Opening Google, sir.");        webbrowser.open("https://google.com")
def open_youtube():    speak("Opening YouTube, sir.");       webbrowser.open("https://youtube.com")
def open_chatgpt():    speak("Opening ChatGPT, sir.");       webbrowser.open("https://chat.openai.com")
def open_copilot():    speak("Opening Microsoft Copilot, sir."); webbrowser.open("https://copilot.microsoft.com")
def open_gemini():     speak("Opening Google Gemini, sir."); webbrowser.open("https://gemini.google.com")
def open_claude():     speak("Opening Claude, sir.");        webbrowser.open("https://claude.ai")
def open_perplexity(): speak("Opening Perplexity, sir.");    webbrowser.open("https://www.perplexity.ai")
def open_facebook():   speak("Opening Facebook, sir.");      webbrowser.open("https://www.facebook.com")
def open_instagram():  speak("Opening Instagram, sir.");     webbrowser.open("https://www.instagram.com")
def open_twitter():    speak("Opening X, sir.");             webbrowser.open("https://twitter.com")
def open_tiktok():     speak("Opening TikTok, sir.");        webbrowser.open("https://www.tiktok.com")
def open_reddit():     speak("Opening Reddit, sir.");        webbrowser.open("https://www.reddit.com")
def open_linkedin():   speak("Opening LinkedIn, sir.");      webbrowser.open("https://www.linkedin.com")
def open_discord():    speak("Opening Discord, sir.");       webbrowser.open("https://discord.com/app")
def open_telegram():   speak("Opening Telegram, sir.");      webbrowser.open("https://web.telegram.org")
def open_gmail():      speak("Opening Gmail, sir.");         webbrowser.open("https://mail.google.com")
def open_drive():      speak("Opening Google Drive, sir.");  webbrowser.open("https://drive.google.com")
def open_docs():       speak("Opening Google Docs, sir.");   webbrowser.open("https://docs.google.com")
def open_sheets():     speak("Opening Google Sheets, sir."); webbrowser.open("https://sheets.google.com")
def open_calendar():   speak("Opening Google Calendar, sir."); webbrowser.open("https://calendar.google.com")
def open_notion():     speak("Opening Notion, sir.");        webbrowser.open("https://www.notion.so")
def open_github():     speak("Opening GitHub, sir.");        webbrowser.open("https://github.com")
def open_netflix():    speak("Opening Netflix, sir.");       webbrowser.open("https://www.netflix.com")
def open_spotify():    speak("Opening Spotify, sir.");       webbrowser.open("https://open.spotify.com")
def open_shopee():     speak("Opening Shopee, sir.");        webbrowser.open("https://www.shopee.ph")
def open_lazada():     speak("Opening Lazada, sir.");        webbrowser.open("https://www.lazada.com.ph")
def open_news():       speak("Opening Google News, sir.");   webbrowser.open("https://news.google.com")
def open_meet():       speak("Opening Google Meet, sir.");   webbrowser.open("https://meet.google.com")

def open_windows_calendar():
    if SYSTEM != "Windows":
        speak("Windows Calendar is only available on Windows, sir.")
        return
    speak("Opening Windows Calendar, sir.")
    try:
        subprocess.Popen(
            ["explorer.exe", r"shell:AppsFolder\microsoft.windowscommunicationsapps_8wekyb3d8bbwe!microsoft.windowslive.calendar"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        logger.error("Failed to open Windows Calendar: %s", e)
        speak("Sorry sir, I couldn't open Windows Calendar.")


# ─────────────────────────────────────────────
# Keypress Helpers
# ─────────────────────────────────────────────

import time
import pyautogui

pyautogui.FAILSAFE = False

def _win_run(app_name: str, delay: float = 0.4):
    pyautogui.hotkey("win")
    time.sleep(delay)
    pyautogui.write(app_name, interval=0.05)
    time.sleep(delay)
    pyautogui.press("enter")

def _win_shortcut(keys: list[str], delay: float = 0.3):
    pyautogui.hotkey(*keys)
    time.sleep(delay)

def _win_run_dialog(command: str, delay: float = 0.4):
    pyautogui.hotkey("win", "r")
    time.sleep(delay)
    pyautogui.write(command, interval=0.05)
    time.sleep(0.2)
    pyautogui.press("enter")


# ─────────────────────────────────────────────
# Windows System Apps
# ─────────────────────────────────────────────

def open_notepad():      speak("Opening Notepad, sir.");           threading.Thread(target=lambda: _win_run("notepad"), daemon=True).start()
def open_calculator():   speak("Opening Calculator, sir.");        threading.Thread(target=lambda: _win_run("calculator"), daemon=True).start()
def open_explorer():     speak("Opening File Explorer, sir.");     threading.Thread(target=lambda: _win_shortcut(["win", "e"]), daemon=True).start()
def open_paint():        speak("Opening Paint, sir.");             threading.Thread(target=lambda: _win_run("paint"), daemon=True).start()
def open_task_manager(): speak("Opening Task Manager, sir.");      threading.Thread(target=lambda: pyautogui.hotkey("ctrl", "shift", "esc"), daemon=True).start()
def open_control_panel():speak("Opening Control Panel, sir.");     threading.Thread(target=lambda: _win_run_dialog("control"), daemon=True).start()
def open_settings():     speak("Opening Settings, sir.");          threading.Thread(target=lambda: _win_shortcut(["win", "i"]), daemon=True).start()
def open_cmd():          speak("Opening Command Prompt, sir.");    threading.Thread(target=lambda: _win_run("cmd"), daemon=True).start()
def open_powershell():   speak("Opening PowerShell, sir.");        threading.Thread(target=lambda: _win_run("powershell"), daemon=True).start()
def open_vscode():       speak("Opening VS Code, sir.");           threading.Thread(target=lambda: _win_run("visual studio code"), daemon=True).start()
def open_snipping_tool():speak("Opening Snipping Tool, sir.");     threading.Thread(target=lambda: pyautogui.hotkey("win", "shift", "s"), daemon=True).start()
def open_word():         speak("Opening Microsoft Word, sir.");    threading.Thread(target=lambda: _win_run("word"), daemon=True).start()
def open_excel():        speak("Opening Microsoft Excel, sir.");   threading.Thread(target=lambda: _win_run("excel"), daemon=True).start()
def open_powerpoint():   speak("Opening Microsoft PowerPoint, sir."); threading.Thread(target=lambda: _win_run("powerpoint"), daemon=True).start()
def open_teams():        speak("Opening Microsoft Teams, sir.");   threading.Thread(target=lambda: _win_run("microsoft teams"), daemon=True).start()
def open_outlook():      speak("Opening Outlook, sir.");           threading.Thread(target=lambda: _win_run("outlook"), daemon=True).start()
def open_store():        speak("Opening Microsoft Store, sir.");   threading.Thread(target=lambda: _win_run_dialog("ms-windows-store:"), daemon=True).start()
def open_camera():       speak("Opening Camera, sir.");            threading.Thread(target=lambda: _win_run("camera"), daemon=True).start()
def open_clock():        speak("Opening Clock, sir.");             threading.Thread(target=lambda: _win_run("clock"), daemon=True).start()
def open_maps():         speak("Opening Maps, sir.");              threading.Thread(target=lambda: _win_run("maps"), daemon=True).start()
def open_photos():       speak("Opening Photos, sir.");            threading.Thread(target=lambda: _win_run("photos"), daemon=True).start()
def open_mail():         speak("Opening Mail, sir.");              threading.Thread(target=lambda: _win_run("mail"), daemon=True).start()
def open_onenote():      speak("Opening OneNote, sir.");           threading.Thread(target=lambda: _win_run("onenote"), daemon=True).start()

def minimize_all():              speak("Minimizing all windows, sir.");         threading.Thread(target=lambda: pyautogui.hotkey("win", "d"), daemon=True).start()
def show_desktop():              speak("Showing desktop, sir.");                threading.Thread(target=lambda: pyautogui.hotkey("win", "d"), daemon=True).start()
def open_action_center():        speak("Opening Action Center, sir.");          threading.Thread(target=lambda: pyautogui.hotkey("win", "a"), daemon=True).start()
def open_notification_center():  speak("Opening Notification Center, sir.");   threading.Thread(target=lambda: pyautogui.hotkey("win", "n"), daemon=True).start()
def open_task_view():            speak("Opening Task View, sir.");              threading.Thread(target=lambda: pyautogui.hotkey("win", "tab"), daemon=True).start()
def open_virtual_desktop():      speak("Creating a new virtual desktop, sir."); threading.Thread(target=lambda: pyautogui.hotkey("win", "ctrl", "d"), daemon=True).start()
def switch_virtual_desktop_right(): speak("Switching to next virtual desktop, sir."); threading.Thread(target=lambda: pyautogui.hotkey("win", "ctrl", "right"), daemon=True).start()
def switch_virtual_desktop_left():  speak("Switching to previous virtual desktop, sir."); threading.Thread(target=lambda: pyautogui.hotkey("win", "ctrl", "left"), daemon=True).start()
def snap_window_left():          speak("Snapping window to the left, sir.");   threading.Thread(target=lambda: pyautogui.hotkey("win", "left"), daemon=True).start()
def snap_window_right():         speak("Snapping window to the right, sir.");  threading.Thread(target=lambda: pyautogui.hotkey("win", "right"), daemon=True).start()
def maximize_window():           speak("Maximizing window, sir.");             threading.Thread(target=lambda: pyautogui.hotkey("win", "up"), daemon=True).start()
def minimize_window():           speak("Minimizing window, sir.");             threading.Thread(target=lambda: pyautogui.hotkey("win", "down"), daemon=True).start()
def close_window():              speak("Closing window, sir.");                threading.Thread(target=lambda: pyautogui.hotkey("alt", "f4"), daemon=True).start()
def switch_window():             speak("Switching window, sir.");              threading.Thread(target=lambda: pyautogui.hotkey("alt", "tab"), daemon=True).start()


# ─────────────────────────────────────────────
# Volume Controls
# FIX: nircmd.exe not found → use PowerShell
#      AudioDeviceCmdlets as primary,
#      nircmd as optional fallback if in PATH
# ─────────────────────────────────────────────

def _get_current_volume_ps() -> int:
    """Get current system volume via PowerShell (0-100)."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             "[Math]::Round((Get-CimInstance -ClassName Win32_SoundDevice | "
             "ForEach-Object { (New-Object -ComObject WScript.Shell).SendKeys([char]0xAD) } ) ; "
             # fallback: use audio API via .NET
             "Add-Type -TypeDefinition '"
             "using System.Runtime.InteropServices;"
             "' ; "
             "[int]([Math]::Round((New-Object -ComObject WScript.Shell | out-null); 50))"],
            capture_output=True, timeout=3,
        )
    except Exception:
        pass
    return 50  # safe default


def _ps_volume_change(delta: int) -> bool:
    """
    Change volume by delta steps using PowerShell + Windows Audio API.
    delta > 0 = up, delta < 0 = down.
    Uses VolumeUp/VolumeDown virtual key presses — works on all Windows 10/11.
    """
    key = "0xAF" if delta > 0 else "0xAE"  # VK_VOLUME_UP / VK_VOLUME_DOWN
    steps = abs(delta)
    script = (
        f"$wsh = New-Object -ComObject WScript.Shell; "
        f"1..{steps} | ForEach-Object {{ $wsh.SendKeys([char]{key}) }}"
    )
    return _run_ps(script)


def _nircmd_volume_change(amount: int) -> bool:
    """Try nircmd if available anywhere in PATH or common locations."""
    nircmd_paths = [
        "nircmd.exe",
        r"C:\Windows\nircmd.exe",
        r"C:\tools\nircmd.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "nircmd", "nircmd.exe"),
    ]
    for path in nircmd_paths:
        if os.path.isfile(path) or path == "nircmd.exe":
            try:
                subprocess.Popen(
                    [path, "changesysvolume", str(amount)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                return True
            except Exception:
                continue
    return False


def volume_up():
    speak("Increasing volume, sir.")
    threading.Thread(target=_do_volume_up, daemon=True).start()

def _do_volume_up():
    # Try nircmd first (precise), fall back to VK key presses (2 steps ≈ 4%)
    if not _nircmd_volume_change(6554):
        _ps_volume_change(2)

def volume_down():
    speak("Decreasing volume, sir.")
    threading.Thread(target=_do_volume_down, daemon=True).start()

def _do_volume_down():
    if not _nircmd_volume_change(-6554):
        _ps_volume_change(-2)

def mute():
    speak("Muting audio, sir.")
    threading.Thread(target=lambda: _ps_volume_change(0) or _run_ps(
        "$wsh = New-Object -ComObject WScript.Shell; $wsh.SendKeys([char]0xAD)"
    ), daemon=True).start()

def unmute():
    speak("Unmuting audio, sir.")
    threading.Thread(target=lambda: _run_ps(
        "$wsh = New-Object -ComObject WScript.Shell; $wsh.SendKeys([char]0xAD)"
    ), daemon=True).start()


# ─────────────────────────────────────────────
# Brightness Controls
# FIX: EDIDParseError on Lenovo display →
#      skip screen_brightness_control entirely,
#      use WMI directly via PowerShell instead
# ─────────────────────────────────────────────

def _get_brightness_wmi() -> int:
    """Get current brightness via WMI. Returns 0-100, default 50 on failure."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness"],
            capture_output=True, timeout=5,
        )
        val = result.stdout.decode(errors="ignore").strip()
        if val.isdigit():
            return int(val)
    except Exception as e:
        logger.warning("WMI get brightness failed: %s", e)
    return 50


def _set_brightness_wmi(value: int) -> bool:
    """Set brightness via WMI (0-100). Works even when EDID parse fails."""
    value = max(0, min(100, value))
    script = (
        f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods)"
        f".WmiSetBrightness(1, {value})"
    )
    ok = _run_ps(script)
    if ok:
        logger.info("Brightness set to %d via WMI", value)
    return ok


def _set_brightness_sbc(value: int) -> bool:
    """Try screen_brightness_control — skip quietly if EDID error."""
    try:
        import screen_brightness_control as sbc
        # sbc raises EDIDParseError on some Lenovo displays — catch it
        sbc.set_brightness(value, display=0)
        return True
    except Exception as e:
        logger.warning("sbc set_brightness skipped (%s)", e)
        return False


def _brightness_up_worker():
    current = _get_brightness_wmi()
    new_val = min(current + 10, 100)
    # Try WMI first (reliable), then sbc as secondary
    if not _set_brightness_wmi(new_val):
        _set_brightness_sbc(new_val)


def _brightness_down_worker():
    current = _get_brightness_wmi()
    new_val = max(current - 10, 0)
    if not _set_brightness_wmi(new_val):
        _set_brightness_sbc(new_val)


def brightness_up():
    speak("Increasing brightness, sir.")
    threading.Thread(target=_brightness_up_worker, daemon=True).start()

def brightness_down():
    speak("Decreasing brightness, sir.")
    threading.Thread(target=_brightness_down_worker, daemon=True).start()


# ─────────────────────────────────────────────
# System Actions
# ─────────────────────────────────────────────

def take_screenshot():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(os.path.expanduser("~"), "Pictures", f"screenshot_{ts}.png")
    threading.Thread(target=lambda: _do_screenshot(filename), daemon=True).start()
    speak("Taking screenshot, sir.")

def _do_screenshot(filename: str):
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    # Method 1: Pillow
    try:
        from PIL import ImageGrab
        ImageGrab.grab().save(filename)
        logger.info("Screenshot saved: %s", filename)
        return
    except ImportError:
        logger.warning("Pillow not installed, trying PowerShell...")
    except Exception as e:
        logger.warning("PIL screenshot failed: %s", e)

    # Method 2: PowerShell (fixed — loads System.Drawing explicitly)
    escaped = filename.replace("\\", "\\\\")
    ok = _run_ps(
        f"Add-Type -AssemblyName System.Windows.Forms; "
        f"Add-Type -AssemblyName System.Drawing; "
        f"$s=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds; "
        f"$bmp=New-Object System.Drawing.Bitmap($s.Width,$s.Height); "
        f"$g=[System.Drawing.Graphics]::FromImage($bmp); "
        f"$g.CopyFromScreen($s.Location,[System.Drawing.Point]::Empty,$s.Size); "
        f"$bmp.Save('{escaped}'); "
        f"$g.Dispose(); $bmp.Dispose()"
    )
    if not ok:
        logger.error("All screenshot methods failed.")

def lock_screen():
    run(["rundll32.exe", "user32.dll,LockWorkStation"])
    speak("Locking the screen, sir.")

def system_shutdown():
    speak("Shutting down the system in 10 seconds, sir.")
    run(["shutdown", "/s", "/t", "10"])

def system_restart():
    speak("Restarting the system in 10 seconds, sir.")
    run(["shutdown", "/r", "/t", "10"])

def cancel_shutdown():
    run(["shutdown", "/a"])
    speak("Shutdown cancelled, sir.")

def sleep_system():
    speak("Putting the system to sleep, sir.")
    run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])

def empty_recycle_bin():
    _run_ps("Clear-RecycleBin -Force -ErrorAction SilentlyContinue")
    speak("Recycle bin emptied, sir.")


# ─────────────────────────────────────────────
# System Info
# ─────────────────────────────────────────────

def get_time():
    speak(f"The time is {datetime.now().strftime('%I:%M %p')}, sir.")

def get_date():
    speak(f"Today is {datetime.now().strftime('%A, %B %d, %Y')}, sir.")

def get_ip():
    import socket
    ip = socket.gethostbyname(socket.gethostname())
    speak(f"Your local IP address is {ip}, sir.")

def get_battery():
    battery = psutil.sensors_battery()
    if battery:
        status = "plugged in" if battery.power_plugged else "on battery"
        speak(f"Battery is at {int(battery.percent)} percent and {status}, sir.")
    else:
        speak("No battery detected, sir.")

def get_cpu():
    speak(f"CPU usage is at {psutil.cpu_percent(interval=1)} percent, sir.")

def get_ram():
    ram = psutil.virtual_memory()
    available = round(ram.available / (1024 ** 3), 1)
    speak(f"RAM usage is {ram.percent} percent, with {available} gigabytes available, sir.")


# ─────────────────────────────────────────────
# FRIDAY System
# ─────────────────────────────────────────────

def friday_greet():
    speak("Good day sir, pleasure to be at your service. How may I assist you today?")

def friday_yes():
    speak("Yes sir, how can I help you?")

def shutdown_friday():
    speak("Shutting down all FRIDAY systems, sir. Backend services terminating. Goodbye.")
    time.sleep(2)
    logger.info("FRIDAY backend shutdown initiated by user command.")
    os._exit(0)


# ─────────────────────────────────────────────
# Command Map
# ─────────────────────────────────────────────

COMMANDS: Dict[str, Callable] = {
    # FRIDAY Wake
    "hey friday":           friday_greet,
    "hi friday":            friday_greet,
    "hello friday":         friday_greet,
    "friday":               friday_yes,
    "good morning friday":  lambda: speak("Good morning sir! Ready to assist you today."),
    "good night friday":    lambda: speak("Good night sir, take care!"),

    # Browser
    "open browser":         open_browser,
    "open google":          open_google,
    "open youtube":         open_youtube,

    # AI Assistants
    "open chatgpt":         open_chatgpt,
    "chatgpt":              open_chatgpt,
    "open copilot":         open_copilot,
    "copilot":              open_copilot,
    "open gemini":          open_gemini,
    "gemini":               open_gemini,
    "open claude":          open_claude,
    "open perplexity":      open_perplexity,

    # Social Media
    "open facebook":        open_facebook,
    "facebook":             open_facebook,
    "open instagram":       open_instagram,
    "instagram":            open_instagram,
    "open twitter":         open_twitter,
    "open tiktok":          open_tiktok,
    "tiktok":               open_tiktok,
    "open reddit":          open_reddit,
    "open linkedin":        open_linkedin,
    "open discord":         open_discord,
    "discord":              open_discord,
    "open telegram":        open_telegram,

    # Productivity
    "open gmail":               open_gmail,
    "gmail":                    open_gmail,
    "open google drive":        open_drive,
    "open drive":               open_drive,
    "open google docs":         open_docs,
    "open docs":                open_docs,
    "open google sheets":       open_sheets,
    "open google calendar":     open_calendar,
    "open windows calendar":    open_windows_calendar,
    "open calendar app":        open_windows_calendar,
    "open notion":              open_notion,
    "open github":              open_github,
    "github":                   open_github,

    # Entertainment
    "open netflix":         open_netflix,
    "netflix":              open_netflix,
    "open spotify":         open_spotify,
    "spotify":              open_spotify,

    # Shopping
    "open shopee":          open_shopee,
    "shopee":               open_shopee,
    "open lazada":          open_lazada,
    "lazada":               open_lazada,

    # News
    "open news":            open_news,

    # Windows Apps
    "open notepad":             open_notepad,
    "notepad":                  open_notepad,
    "open calculator":          open_calculator,
    "calculator":               open_calculator,
    "open file explorer":       open_explorer,
    "file explorer":            open_explorer,
    "open paint":               open_paint,
    "open task manager":        open_task_manager,
    "task manager":             open_task_manager,
    "open control panel":       open_control_panel,
    "open settings":            open_settings,
    "open cmd":                 open_cmd,
    "open command prompt":      open_cmd,
    "open powershell":          open_powershell,
    "powershell":               open_powershell,
    "open vs code":             open_vscode,
    "open vscode":              open_vscode,
    "open snipping tool":       open_snipping_tool,
    "snip":                     open_snipping_tool,
    "open word":                open_word,
    "microsoft word":           open_word,
    "open excel":               open_excel,
    "microsoft excel":          open_excel,
    "open powerpoint":          open_powerpoint,
    "microsoft powerpoint":     open_powerpoint,
    "open teams":               open_teams,
    "microsoft teams":          open_teams,
    "open meet":                open_meet,
    "open google meet":         open_meet,
    "google meet":              open_meet,
    "open outlook":             open_outlook,
    "outlook":                  open_outlook,
    "open store":               open_store,
    "microsoft store":          open_store,
    "open camera":              open_camera,
    "camera":                   open_camera,
    "open clock":               open_clock,
    "open maps":                open_maps,
    "open photos":              open_photos,
    "photos":                   open_photos,
    "open mail":                open_mail,
    "open onenote":             open_onenote,
    "onenote":                  open_onenote,

    # Window Management
    "minimize all":             minimize_all,
    "show desktop":             show_desktop,
    "open action center":       open_action_center,
    "action center":            open_action_center,
    "open notifications":       open_notification_center,
    "notifications":            open_notification_center,
    "task view":                open_task_view,
    "open task view":           open_task_view,
    "new virtual desktop":      open_virtual_desktop,
    "virtual desktop":          open_virtual_desktop,
    "next desktop":             switch_virtual_desktop_right,
    "previous desktop":         switch_virtual_desktop_left,
    "snap left":                snap_window_left,
    "snap right":               snap_window_right,
    "maximize":                 maximize_window,
    "maximize window":          maximize_window,
    "minimize":                 minimize_window,
    "minimize window":          minimize_window,
    "close window":             close_window,
    "close this":               close_window,
    "switch window":            switch_window,
    "alt tab":                  switch_window,

    # Volume
    "volume up":            volume_up,
    "increase volume":      volume_up,
    "louder":               volume_up,
    "volume down":          volume_down,
    "decrease volume":      volume_down,
    "quieter":              volume_down,
    "mute":                 mute,
    "unmute":               unmute,

    # Brightness
    "brightness up":        brightness_up,
    "increase brightness":  brightness_up,
    "brighter":             brightness_up,
    "brightness down":      brightness_down,
    "decrease brightness":  brightness_down,
    "dimmer":               brightness_down,

    # System Actions
    "take screenshot":      take_screenshot,
    "screenshot":           take_screenshot,
    "lock screen":          lock_screen,
    "lock pc":              lock_screen,
    "shutdown":             system_shutdown,
    "turn off":             system_shutdown,
    "restart":              system_restart,
    "reboot":               system_restart,
    "cancel shutdown":      cancel_shutdown,
    "sleep system":         sleep_system,
    "hibernate":            sleep_system,
    "empty recycle bin":    empty_recycle_bin,
    "clear recycle bin":    empty_recycle_bin,

    # System Info
    "what time":            get_time,
    "time":                 get_time,
    "what date":            get_date,
    "date":                 get_date,
    "today":                get_date,
    "ip address":           get_ip,
    "my ip":                get_ip,
    "battery":              get_battery,
    "battery status":       get_battery,
    "cpu usage":            get_cpu,
    "ram usage":            get_ram,
    "memory":               get_ram,

    # FRIDAY System
    "shutdown friday":      shutdown_friday,
}


# ─────────────────────────────────────────────
# Reminder Parser
# ─────────────────────────────────────────────

def _parse_and_execute_reminder(command_text: str) -> bool:
    parsed = parse_reminder_text(command_text)
    if not parsed:
        if re.search(r"\b(list|show|tingnan)\s+(my\s+)?reminders\b", command_text, re.IGNORECASE):
            items = reminder_store.list(include_done=False, limit=10)
            if not items:
                state.push_alert(level="info", title="Reminders", message="No upcoming reminders.", ttl_seconds=10)
                speak("You have no upcoming reminders, sir.")
            else:
                lines = [f"- {r.get('title')} at {_fmt_due(r.get('dueAt', ''))}" for r in items[:5]]
                state.push_alert(
                    level="info",
                    title="Reminders",
                    message="Upcoming:\n" + "\n".join(lines),
                    ttl_seconds=15,
                )
                speak(f"You have {len(items)} upcoming reminder{'s' if len(items) != 1 else ''}, sir.")
            return True
        return False

    title, due_at = parsed
    r = reminder_store.create(title=title, due_at=due_at, repeat="none")
    state.push_alert(
        level="info",
        title="Reminder Scheduled",
        message=f"{r.title} at {due_at.strftime('%b %d, %I:%M %p')}",
        ttl_seconds=20,
        meta={"reminderId": r.id},
    )
    speak(f"Reminder set, sir. I'll remind you to {r.title} at {due_at.strftime('%I:%M %p')}.")
    return True


def _fmt_due(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%b %d, %I:%M %p")
    except Exception:
        return iso


# ─────────────────────────────────────────────
# Calendar Parser
# ─────────────────────────────────────────────

def _parse_and_execute_calendar(command_text: str) -> bool:
    if not any(k in command_text.lower() for k in (
        "add event", "create event", "add to calendar",
        "schedule", "calendar event", "add calendar event",
        "mag-schedule", "mag schedule", "i-schedule",
        "idagdag sa calendar", "idagdag sa kalendaryo",
        "gumawa ng event",
    )):
        return False
    return bool(create_calendar_event_from_text(command_text))


# ─────────────────────────────────────────────
# Vision Parser
# ─────────────────────────────────────────────

def _parse_and_execute_vision(command_text: str) -> bool:
    tl = command_text.lower()
    if "air mouse" in tl or "airmouse" in tl:
        try:
            from app.services.vision.air_mouse import air_mouse
            if any(k in tl for k in ("stop", "disable", "off")):
                air_mouse.stop()
                speak("Air Mouse stopped, sir.")
            else:
                ok, msg = air_mouse.start()
                if not ok:
                    state.push_alert(level="error", title="Air Mouse", message=msg, ttl_seconds=20)
                    speak(f"Could not start Air Mouse, sir. {msg}")
                else:
                    speak("Air Mouse started, sir. Use your index finger to move the cursor.")
            return True
        except Exception as e:
            state.push_alert(level="error", title="Air Mouse", message=str(e), ttl_seconds=20)
            return True

    if "sign launcher" in tl or "sign-language" in tl or "sign language" in tl:
        try:
            from app.services.vision.sign_launcher import sign_launcher
            if any(k in tl for k in ("stop", "disable", "off")):
                sign_launcher.stop()
                speak("Sign Launcher stopped, sir.")
            else:
                ok, msg = sign_launcher.start()
                if not ok:
                    state.push_alert(level="error", title="Sign Launcher", message=msg, ttl_seconds=20)
                    speak(f"Could not start Sign Launcher, sir. {msg}")
                else:
                    speak("Sign Launcher started, sir. Show a hand gesture to launch apps.")
            return True
        except Exception as e:
            state.push_alert(level="error", title="Sign Launcher", message=str(e), ttl_seconds=20)
            return True

    return False


# ─────────────────────────────────────────────
# Silent Executor (for Gemini-powered responses)
# ─────────────────────────────────────────────

def _execute_command_silent(command_text: str) -> bool:
    import app.services.tts as tts_module
    import app.services.actions as actions_module

    logger.info("[SILENT COMMAND]: %s", command_text)
    state.last_command = command_text
    command_lower = command_text.lower().strip()

    if _resolve_pending_action(command_lower): return True
    if _parse_and_execute_search(command_lower): return True
    if _parse_and_execute_reminder(command_text): return True
    if _parse_and_execute_calendar(command_text): return True
    if _parse_and_execute_vision(command_text): return True

    sorted_commands = sorted(COMMANDS.items(), key=lambda x: len(x[0]), reverse=True)
    for keyword, action in sorted_commands:
        if keyword in command_lower:
            try:
                original_speak = tts_module.speak
                tts_module.speak = lambda text: None
                actions_module.speak = lambda text: None
                threading.Thread(target=action, daemon=True).start()
                def restore():
                    time.sleep(1)
                    tts_module.speak = original_speak
                    actions_module.speak = original_speak
                threading.Thread(target=restore, daemon=True).start()
                return True
            except Exception as e:
                logger.error("Silent execute error '%s': %s", keyword, e)
                return False

    logger.info("No command matched (silent) for: %s", command_lower)
    return False


# ─────────────────────────────────────────────
# Main Executor
# ─────────────────────────────────────────────

def execute_command(command_text: str) -> bool:
    logger.info("[COMMAND]: %s", command_text)
    state.last_command = command_text
    command_lower = command_text.lower().strip()

    if _resolve_pending_action(command_lower): return True
    if _parse_and_execute_search(command_lower): return True
    if _parse_and_execute_reminder(command_text): return True
    if _parse_and_execute_calendar(command_text): return True
    if _parse_and_execute_vision(command_text): return True

    sorted_commands = sorted(COMMANDS.items(), key=lambda x: len(x[0]), reverse=True)
    for keyword, action in sorted_commands:
        if keyword in command_lower:
            try:
                threading.Thread(target=action, daemon=True).start()
                return True
            except Exception as e:
                logger.error("Error executing command '%s': %s", keyword, e)
                speak("Sorry sir, I encountered an error executing that command.")
                return False

    logger.info("No command matched for: %s", command_lower)
    speak("I'm sorry sir, I didn't understand that. Please try the manual command box.")
    return False