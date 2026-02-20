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


# ─────────────────────────────────────────────
# Search Functions
# ─────────────────────────────────────────────

def search_google(query: str):
    """Search Google for a given query."""
    encoded = urllib.parse.quote(query)
    url = f"https://www.google.com/search?q={encoded}"
    speak(f"Searching Google for {query}, sir.")
    webbrowser.open(url)

def search_youtube(query: str):
    """Search YouTube for a given query."""
    encoded = urllib.parse.quote(query)
    url = f"https://www.youtube.com/results?search_query={encoded}"
    speak(f"Searching YouTube for {query}, sir.")
    webbrowser.open(url)

def play_music(query: str):
    """Play music on YouTube."""
    encoded = urllib.parse.quote(query)
    url = f"https://www.youtube.com/results?search_query={encoded}"
    speak(f"Playing {query} on YouTube, sir.")
    webbrowser.open(url)

def search_spotify(query: str):
    """Search Spotify for a given query."""
    encoded = urllib.parse.quote(query)
    url = f"https://open.spotify.com/search/{encoded}"
    speak(f"Searching Spotify for {query}, sir.")
    webbrowser.open(url)

def search_reddit(query: str):
    """Search Reddit for a given query."""
    encoded = urllib.parse.quote(query)
    url = f"https://www.reddit.com/search/?q={encoded}"
    speak(f"Searching Reddit for {query}, sir.")
    webbrowser.open(url)

def search_github(query: str):
    """Search GitHub for a given query."""
    encoded = urllib.parse.quote(query)
    url = f"https://github.com/search?q={encoded}"
    speak(f"Searching GitHub for {query}, sir.")
    webbrowser.open(url)


# ─────────────────────────────────────────────
# Pending Action Handler
# Resolves follow-up queries after clarification prompts.
#
# Flow example:
#   User:   "search"
#   FRIDAY: "Ano ang isesearch ko para sa iyo, sir?"
#           → state.pending_action = "search_google"
#   User:   "kabinalismo"
#   FRIDAY: "Searching Google for kabinalismo, sir."
# ─────────────────────────────────────────────

def _resolve_pending_action(command_text: str) -> bool:
    """
    If state.pending_action is set, treat the current command_text as
    the answer/query and execute the stored action.
    Returns True if a pending action was resolved.
    """
    pending = getattr(state, "pending_action", None)
    if not pending:
        return False

    # Clear immediately so it doesn't loop
    state.pending_action = None
    query = command_text.strip()

    if pending == "search_google":
        search_google(query)
        return True
    elif pending == "search_youtube":
        search_youtube(query)
        return True
    elif pending == "play_music":
        play_music(query)
        return True
    elif pending == "search_spotify":
        search_spotify(query)
        return True
    elif pending == "search_reddit":
        search_reddit(query)
        return True
    elif pending == "search_github":
        search_github(query)
        return True

    return False


# ─────────────────────────────────────────────
# Dynamic Search Command Parser
# Handles: "search X", "search X on google/youtube/spotify"
#          "play X", "play X on spotify/youtube"
#          "search X and play Y", "search X then play Y"
#          bare "search" / "play" / "play music" → asks clarification
# ─────────────────────────────────────────────

def _parse_and_execute_search(command_lower: str) -> bool:
    """
    Parses flexible search/play commands and executes them.
    Returns True if a search action was performed or clarification was asked.

    Supported patterns:
      - "search kabinalismo"
      - "search kabinalismo on youtube / google / spotify / reddit / github"
      - "play sinta by moonstar88"
      - "play music kabinalismo"
      - "play sinta on spotify / youtube"
      - "search kabinalismo and play the music"
      - "search kabinalismo then play sinta"
      - bare "search"           → asks "Ano ang isesearch ko para sa iyo, sir?"
      - bare "play" / "play music" → asks "Anong kanta ang ipe-play ko, sir?"
      - bare "youtube search"   → asks "Ano ang hahanaping ko sa YouTube, sir?"
    """

    # ── Pattern: "search X and/then play Y" / "search X and play the music" ──
    m = re.search(
        r"search\s+(.+?)\s+(?:and|then)\s+play(?:\s+(?:the\s+)?(?:music|song))?\s*(.*)",
        command_lower
    )
    if m:
        search_query = m.group(1).strip()
        play_query   = m.group(2).strip() or search_query  # fallback: same as search
        speak(f"Searching for {search_query} and playing {play_query}, sir.")
        webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote(search_query)}")
        import time; time.sleep(1)
        webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote(play_query)}")
        return True

    # ── Pattern: "play X on spotify" ─────────────────────────────────────────
    m = re.search(r"play\s+(.+?)\s+on\s+spotify", command_lower)
    if m:
        search_spotify(m.group(1).strip())
        return True

    # ── Pattern: "play X on youtube" ─────────────────────────────────────────
    m = re.search(r"play\s+(.+?)\s+on\s+youtube", command_lower)
    if m:
        play_music(m.group(1).strip())
        return True

    # ── Pattern: "search X on youtube" ───────────────────────────────────────
    m = re.search(r"search\s+(.+?)\s+on\s+youtube", command_lower)
    if m:
        search_youtube(m.group(1).strip())
        return True

    # ── Pattern: "search X on spotify" ───────────────────────────────────────
    m = re.search(r"search\s+(.+?)\s+on\s+spotify", command_lower)
    if m:
        search_spotify(m.group(1).strip())
        return True

    # ── Pattern: "search X on reddit" ────────────────────────────────────────
    m = re.search(r"search\s+(.+?)\s+on\s+reddit", command_lower)
    if m:
        search_reddit(m.group(1).strip())
        return True

    # ── Pattern: "search X on github" ────────────────────────────────────────
    m = re.search(r"search\s+(.+?)\s+on\s+github", command_lower)
    if m:
        search_github(m.group(1).strip())
        return True

    # ── Pattern: "search X on google" / "google X" ───────────────────────────
    m = re.search(r"(?:search\s+(.+?)\s+on\s+google|^google\s+(.+))", command_lower)
    if m:
        query = (m.group(1) or m.group(2)).strip()
        search_google(query)
        return True

    # ── Pattern: "search X" with actual query (default → Google) ─────────────
    m = re.search(r"^search\s+(.+)", command_lower)
    if m:
        query = m.group(1).strip()
        if query:
            search_google(query)
            return True

    # ── Pattern: bare "search" with no query → ask clarification ─────────────
    if re.match(r"^search\s*$", command_lower):
        speak("Ano ang isesearch ko para sa iyo, sir?")
        state.pending_action = "search_google"
        return True

    # ── Pattern: bare "play" / "play music" / "play song" → ask clarification ─
    if re.match(r"^play\s*(music|song|a\s+song)?\s*$", command_lower):
        speak("Anong kanta ang ipe-play ko, sir?")
        state.pending_action = "play_music"
        return True

    # ── Pattern: "play X" with actual query ──────────────────────────────────
    m = re.search(r"^play\s+(?:music|song|the\s+song)?\s*(.+)", command_lower)
    if m:
        query = m.group(1).strip()
        if query:
            play_music(query)
            return True

    # ── Pattern: "youtube search X" / "look up X" ────────────────────────────
    m = re.search(r"(?:youtube\s+search|look\s+up)\s+(.+)", command_lower)
    if m:
        search_youtube(m.group(1).strip())
        return True

    # ── Pattern: bare "youtube search" / "look up" → ask clarification ───────
    if re.match(r"^(?:youtube\s+search|look\s+up)\s*$", command_lower):
        speak("Ano ang hahanaping ko sa YouTube, sir?")
        state.pending_action = "search_youtube"
        return True

    return False


# ─────────────────────────────────────────────
# Browser / Websites
# ─────────────────────────────────────────────

def open_browser():
    speak("Opening browser, sir.")
    webbrowser.open("https://google.com")

def open_google():
    speak("Opening Google, sir.")
    webbrowser.open("https://google.com")

def open_youtube():
    speak("Opening YouTube, sir.")
    webbrowser.open("https://youtube.com")

def open_chatgpt():
    speak("Opening ChatGPT, sir.")
    webbrowser.open("https://chat.openai.com")

def open_copilot():
    speak("Opening Microsoft Copilot, sir.")
    webbrowser.open("https://copilot.microsoft.com")

def open_gemini():
    speak("Opening Google Gemini, sir.")
    webbrowser.open("https://gemini.google.com")

def open_claude():
    speak("Opening Claude, sir.")
    webbrowser.open("https://claude.ai")

def open_perplexity():
    speak("Opening Perplexity, sir.")
    webbrowser.open("https://www.perplexity.ai")

def open_facebook():
    speak("Opening Facebook, sir.")
    webbrowser.open("https://www.facebook.com")

def open_instagram():
    speak("Opening Instagram, sir.")
    webbrowser.open("https://www.instagram.com")

def open_twitter():
    speak("Opening X, sir.")
    webbrowser.open("https://twitter.com")

def open_tiktok():
    speak("Opening TikTok, sir.")
    webbrowser.open("https://www.tiktok.com")

def open_reddit():
    speak("Opening Reddit, sir.")
    webbrowser.open("https://www.reddit.com")

def open_linkedin():
    speak("Opening LinkedIn, sir.")
    webbrowser.open("https://www.linkedin.com")

def open_discord():
    speak("Opening Discord, sir.")
    webbrowser.open("https://discord.com/app")

def open_telegram():
    speak("Opening Telegram, sir.")
    webbrowser.open("https://web.telegram.org")

def open_gmail():
    speak("Opening Gmail, sir.")
    webbrowser.open("https://mail.google.com")

def open_drive():
    speak("Opening Google Drive, sir.")
    webbrowser.open("https://drive.google.com")

def open_docs():
    speak("Opening Google Docs, sir.")
    webbrowser.open("https://docs.google.com")

def open_sheets():
    speak("Opening Google Sheets, sir.")
    webbrowser.open("https://sheets.google.com")

def open_calendar():
    speak("Opening Google Calendar, sir.")
    webbrowser.open("https://calendar.google.com")

def open_notion():
    speak("Opening Notion, sir.")
    webbrowser.open("https://www.notion.so")

def open_github():
    speak("Opening GitHub, sir.")
    webbrowser.open("https://github.com")

def open_netflix():
    speak("Opening Netflix, sir.")
    webbrowser.open("https://www.netflix.com")

def open_spotify():
    speak("Opening Spotify, sir.")
    webbrowser.open("https://open.spotify.com")

def open_shopee():
    speak("Opening Shopee, sir.")
    webbrowser.open("https://www.shopee.ph")

def open_lazada():
    speak("Opening Lazada, sir.")
    webbrowser.open("https://www.lazada.com.ph")

def open_news():
    speak("Opening Google News, sir.")
    webbrowser.open("https://news.google.com")


# ─────────────────────────────────────────────
# Keypress Helpers
# Requires: pip install pyautogui keyboard
# ─────────────────────────────────────────────

import time
import pyautogui

pyautogui.FAILSAFE = False  # Prevent accidental top-left corner abort

def _win_run(app_name: str, delay: float = 0.4):
    """Press Win, type app name, hit Enter — works for any installed app."""
    pyautogui.hotkey("win")
    time.sleep(delay)
    pyautogui.write(app_name, interval=0.05)
    time.sleep(delay)
    pyautogui.press("enter")

def _win_shortcut(keys: list[str], delay: float = 0.3):
    """Press a Win+key combo, e.g. ['win', 'e'] for File Explorer."""
    pyautogui.hotkey(*keys)
    time.sleep(delay)

def _win_run_dialog(command: str, delay: float = 0.4):
    """Win+R → type command → Enter (for things like ms-settings:, control, etc.)"""
    pyautogui.hotkey("win", "r")
    time.sleep(delay)
    pyautogui.write(command, interval=0.05)
    time.sleep(0.2)
    pyautogui.press("enter")


# ─────────────────────────────────────────────
# Windows System Apps (keypress-based)
# ─────────────────────────────────────────────

def open_notepad():
    speak("Opening Notepad, sir.")
    threading.Thread(target=lambda: _win_run("notepad"), daemon=True).start()

def open_calculator():
    speak("Opening Calculator, sir.")
    threading.Thread(target=lambda: _win_run("calculator"), daemon=True).start()

def open_explorer():
    speak("Opening File Explorer, sir.")
    threading.Thread(target=lambda: _win_shortcut(["win", "e"]), daemon=True).start()

def open_paint():
    speak("Opening Paint, sir.")
    threading.Thread(target=lambda: _win_run("paint"), daemon=True).start()

def open_task_manager():
    speak("Opening Task Manager, sir.")
    threading.Thread(target=lambda: pyautogui.hotkey("ctrl", "shift", "esc"), daemon=True).start()

def open_control_panel():
    speak("Opening Control Panel, sir.")
    threading.Thread(target=lambda: _win_run_dialog("control"), daemon=True).start()

def open_settings():
    speak("Opening Settings, sir.")
    threading.Thread(target=lambda: _win_shortcut(["win", "i"]), daemon=True).start()

def open_cmd():
    speak("Opening Command Prompt, sir.")
    threading.Thread(target=lambda: _win_run("cmd"), daemon=True).start()

def open_powershell():
    speak("Opening PowerShell, sir.")
    threading.Thread(target=lambda: _win_run("powershell"), daemon=True).start()

def open_vscode():
    speak("Opening VS Code, sir.")
    threading.Thread(target=lambda: _win_run("visual studio code"), daemon=True).start()

def open_snipping_tool():
    speak("Opening Snipping Tool, sir.")
    threading.Thread(target=lambda: pyautogui.hotkey("win", "shift", "s"), daemon=True).start()

def open_word():
    speak("Opening Microsoft Word, sir.")
    threading.Thread(target=lambda: _win_run("word"), daemon=True).start()

def open_excel():
    speak("Opening Microsoft Excel, sir.")
    threading.Thread(target=lambda: _win_run("excel"), daemon=True).start()

def open_powerpoint():
    speak("Opening Microsoft PowerPoint, sir.")
    threading.Thread(target=lambda: _win_run("powerpoint"), daemon=True).start()

def open_teams():
    speak("Opening Microsoft Teams, sir.")
    threading.Thread(target=lambda: _win_run("microsoft teams"), daemon=True).start()

def open_outlook():
    speak("Opening Outlook, sir.")
    threading.Thread(target=lambda: _win_run("outlook"), daemon=True).start()

def open_store():
    speak("Opening Microsoft Store, sir.")
    threading.Thread(target=lambda: _win_run_dialog("ms-windows-store:"), daemon=True).start()

def open_camera():
    speak("Opening Camera, sir.")
    threading.Thread(target=lambda: _win_run("camera"), daemon=True).start()

def open_clock():
    speak("Opening Clock, sir.")
    threading.Thread(target=lambda: _win_run("clock"), daemon=True).start()

def open_maps():
    speak("Opening Maps, sir.")
    threading.Thread(target=lambda: _win_run("maps"), daemon=True).start()

def open_photos():
    speak("Opening Photos, sir.")
    threading.Thread(target=lambda: _win_run("photos"), daemon=True).start()

def open_mail():
    speak("Opening Mail, sir.")
    threading.Thread(target=lambda: _win_run("mail"), daemon=True).start()

def open_onenote():
    speak("Opening OneNote, sir.")
    threading.Thread(target=lambda: _win_run("onenote"), daemon=True).start()

def minimize_all():
    speak("Minimizing all windows, sir.")
    threading.Thread(target=lambda: pyautogui.hotkey("win", "d"), daemon=True).start()

def show_desktop():
    speak("Showing desktop, sir.")
    threading.Thread(target=lambda: pyautogui.hotkey("win", "d"), daemon=True).start()

def open_action_center():
    speak("Opening Action Center, sir.")
    threading.Thread(target=lambda: pyautogui.hotkey("win", "a"), daemon=True).start()

def open_notification_center():
    speak("Opening Notification Center, sir.")
    threading.Thread(target=lambda: pyautogui.hotkey("win", "n"), daemon=True).start()

def open_task_view():
    speak("Opening Task View, sir.")
    threading.Thread(target=lambda: pyautogui.hotkey("win", "tab"), daemon=True).start()

def open_virtual_desktop():
    speak("Creating a new virtual desktop, sir.")
    threading.Thread(target=lambda: pyautogui.hotkey("win", "ctrl", "d"), daemon=True).start()

def switch_virtual_desktop_right():
    speak("Switching to next virtual desktop, sir.")
    threading.Thread(target=lambda: pyautogui.hotkey("win", "ctrl", "right"), daemon=True).start()

def switch_virtual_desktop_left():
    speak("Switching to previous virtual desktop, sir.")
    threading.Thread(target=lambda: pyautogui.hotkey("win", "ctrl", "left"), daemon=True).start()

def snap_window_left():
    speak("Snapping window to the left, sir.")
    threading.Thread(target=lambda: pyautogui.hotkey("win", "left"), daemon=True).start()

def snap_window_right():
    speak("Snapping window to the right, sir.")
    threading.Thread(target=lambda: pyautogui.hotkey("win", "right"), daemon=True).start()

def maximize_window():
    speak("Maximizing window, sir.")
    threading.Thread(target=lambda: pyautogui.hotkey("win", "up"), daemon=True).start()

def minimize_window():
    speak("Minimizing window, sir.")
    threading.Thread(target=lambda: pyautogui.hotkey("win", "down"), daemon=True).start()

def close_window():
    speak("Closing window, sir.")
    threading.Thread(target=lambda: pyautogui.hotkey("alt", "f4"), daemon=True).start()

def switch_window():
    speak("Switching window, sir.")
    threading.Thread(target=lambda: pyautogui.hotkey("alt", "tab"), daemon=True).start()


# ─────────────────────────────────────────────
# Volume Controls
# Requires nircmd.exe in PATH
# Download: https://www.nirsoft.net/utils/nircmd.html
# ─────────────────────────────────────────────

def volume_up():
    run(["nircmd.exe", "changesysvolume", "6554"])
    speak("Increasing volume, sir.")

def volume_down():
    run(["nircmd.exe", "changesysvolume", "-6554"])
    speak("Decreasing volume, sir.")

def mute():
    run(["nircmd.exe", "mutesysvolume", "1"])
    speak("Muting audio, sir.")

def unmute():
    run(["nircmd.exe", "mutesysvolume", "0"])
    speak("Unmuting audio, sir.")


# ─────────────────────────────────────────────
# Brightness Controls
# Requires: pip install screen-brightness-control
# ─────────────────────────────────────────────

def brightness_up():
    try:
        import screen_brightness_control as sbc
        current = sbc.get_brightness(display=0)[0]
        sbc.set_brightness(min(current + 10, 100), display=0)
        speak("Increasing brightness, sir.")
    except Exception as e:
        logger.error("Brightness up failed: %s", e)

def brightness_down():
    try:
        import screen_brightness_control as sbc
        current = sbc.get_brightness(display=0)[0]
        sbc.set_brightness(max(current - 10, 0), display=0)
        speak("Decreasing brightness, sir.")
    except Exception as e:
        logger.error("Brightness down failed: %s", e)


# ─────────────────────────────────────────────
# System Actions
# ─────────────────────────────────────────────

def take_screenshot():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run(["nircmd.exe", "savescreenshot", f"screenshot_{ts}.png"])
    speak("Screenshot taken, sir.")

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
    run(["PowerShell.exe", "-Command", "Clear-RecycleBin -Force"])
    speak("Recycle bin emptied, sir.")


# ─────────────────────────────────────────────
# System Info
# ─────────────────────────────────────────────

def get_time():
    current_time = datetime.now().strftime("%I:%M %p")
    speak(f"The time is {current_time}, sir.")

def get_date():
    current_date = datetime.now().strftime("%A, %B %d, %Y")
    speak(f"Today is {current_date}, sir.")

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
    usage = psutil.cpu_percent(interval=1)
    speak(f"CPU usage is at {usage} percent, sir.")

def get_ram():
    ram = psutil.virtual_memory()
    available = round(ram.available / (1024 ** 3), 1)
    speak(f"RAM usage is {ram.percent} percent, with {available} gigabytes available, sir.")


# ─────────────────────────────────────────────
# FRIDAY System
# ─────────────────────────────────────────────

def shutdown_friday():
    speak("Shutting down all FRIDAY systems, sir. Backend services terminating. Goodbye.")
    import time
    time.sleep(2)
    logger.info("FRIDAY backend shutdown initiated by user command.")
    os._exit(0)


# ─────────────────────────────────────────────
# Command Map
# ─────────────────────────────────────────────

COMMANDS: Dict[str, Callable] = {
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
    "open gmail":           open_gmail,
    "gmail":                open_gmail,
    "open google drive":    open_drive,
    "open drive":           open_drive,
    "open google docs":     open_docs,
    "open docs":            open_docs,
    "open google sheets":   open_sheets,
    "open google calendar": open_calendar,
    "open notion":          open_notion,
    "open github":          open_github,
    "github":               open_github,

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
# Silent Executor (for Gemini-powered responses)
# ─────────────────────────────────────────────

def _execute_command_silent(command_text: str) -> bool:
    """Execute command WITHOUT the built-in speak — Gemini will speak instead."""
    import app.services.tts as tts_module
    import app.services.actions as actions_module

    logger.info("[SILENT COMMAND]: %s", command_text)
    state.last_command = command_text
    command_lower = command_text.lower().strip()

    # ── 0. Resolve any pending clarification first ────────────────────────────
    if _resolve_pending_action(command_lower):
        return True

    # ── 1. Try dynamic search/play parser ────────────────────────────────────
    if _parse_and_execute_search(command_lower):
        return True

    # ── 2. Static COMMANDS dict ───────────────────────────────────────────────
    sorted_commands = sorted(COMMANDS.items(), key=lambda x: len(x[0]), reverse=True)

    for keyword, action in sorted_commands:
        if keyword in command_lower:
            try:
                original_speak = tts_module.speak

                def silent_speak(text):
                    pass  # no-op, Gemini already spoke

                tts_module.speak = silent_speak
                actions_module.speak = silent_speak

                threading.Thread(target=action, daemon=True).start()

                def restore_speak():
                    import time
                    time.sleep(1)
                    tts_module.speak = original_speak
                    actions_module.speak = original_speak

                threading.Thread(target=restore_speak, daemon=True).start()
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

    # ── 0. Resolve pending clarification FIRST ────────────────────────────────
    # e.g. FRIDAY asked "Ano ang isesearch ko para sa iyo, sir?"
    #      User replies "kabinalismo" → this handles it
    if _resolve_pending_action(command_lower):
        return True

    # ── 1. Try dynamic search/play parser ────────────────────────────────────
    # Handles: "search X", "play X", "search X and play Y",
    #          bare "search"/"play" → asks clarification
    if _parse_and_execute_search(command_lower):
        return True

    # ── 2. Fall back to static COMMANDS dict ─────────────────────────────────
    # Sort longest keyword first → most specific match wins
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
    speak("I'm sorry sir, I didn't understand that command.")
    return False