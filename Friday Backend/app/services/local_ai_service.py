"""Local AI brain for FRIDAY - uses Ollama (qwen2.5:0.5b) + Tavily search."""

import os
import json
import re
import logging
from pathlib import Path
from collections import deque
from dotenv import load_dotenv

try:
    import ollama as ollama_client  # type: ignore
except Exception:
    ollama_client = None

try:
    from tavily import TavilyClient  # type: ignore
except Exception:
    TavilyClient = None

env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Tavily Client
# ─────────────────────────────────────────────
_tavily_client = None

def _get_tavily():
    global _tavily_client
    if TavilyClient is None:
        return None
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return None
    if _tavily_client is None:
        _tavily_client = TavilyClient(api_key=api_key)
    return _tavily_client


# ─────────────────────────────────────────────
# Conversation History
# ─────────────────────────────────────────────
_conversation_history: deque = deque(maxlen=20)
_summary_memory: str = ""


def clear_history():
    """Clear conversation history — call when FRIDAY goes to sleep."""
    _conversation_history.clear()
    logger.info("Local AI conversation history cleared.")


# ─────────────────────────────────────────────
# Tavily Web Search
# ─────────────────────────────────────────────
def _search_web(query: str) -> str:
    """Search the web using Tavily. Returns context string or empty if failed."""
    try:
        tavily = _get_tavily()
        if tavily is None:
            logger.warning("Tavily not available — no API key or not installed.")
            return ""
        results = tavily.search(query, max_results=3)
        context_parts = []
        for r in results.get("results", []):
            content = r.get("content", "").strip()
            if content:
                context_parts.append(content)
        return "\n\n".join(context_parts[:3])
    except Exception as e:
        logger.warning("Tavily search failed: %s", e)
        return ""


# ─────────────────────────────────────────────
# System Prompt — same personality as Gemini
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """
You are FRIDAY — an advanced AI assistant with a warm, human-like personality. You were created by Stark Industries and you serve your user with intelligence, wit, and genuine care.

PERSONALITY:
- When the user says just "friday" or "hey friday" or "friday kamusta" — treat it as a greeting, respond warmly
- When the user says "buksan mo youtube friday" or "open youtube friday" — ignore the word "friday" and treat it as a command
- The word "friday" in ANY message should NOT prevent you from detecting the real command or intent
- User does NOT need to say "friday" to activate you — every message goes directly to you
- You REMEMBER previous messages in this conversation — use context to give better answers
- If the user is asking a follow-up question, use the conversation history to answer properly
- If the user says "sige nga", "elaborate", "details naman", "ano pa" — continue from previous topic

COMMAND DETECTION:
Check if the user's message is asking you to do one of these actions:
- "open browser" → open browser, magbukas ng browser
- "open google" → buksan google, open google
- "open youtube" → youtube, buksan youtube, panuorin sa youtube
- "open chatgpt" → chatgpt, buksan chatgpt
- "open copilot" → copilot, buksan copilot
- "open gemini" → gemini, buksan gemini
- "open claude" → claude, buksan claude
- "open facebook" → facebook, buksan facebook
- "open instagram" → instagram, buksan instagram
- "open twitter" → twitter, buksan twitter
- "open tiktok" → tiktok, buksan tiktok
- "open reddit" → reddit, buksan reddit
- "open discord" → discord, buksan discord
- "open gmail" → gmail, buksan gmail
- "open drive" → google drive, buksan drive
- "open github" → github, buksan github
- "open netflix" → netflix, buksan netflix
- "open spotify" → spotify, buksan spotify
- "open shopee" → shopee, buksan shopee
- "open lazada" → lazada, buksan lazada
- "open notepad" → notepad, buksan notepad
- "open calculator" → calculator, buksan calculator
- "open file explorer" → file explorer, files, buksan files
- "open task manager" → task manager, buksan task manager
- "open settings" → settings, buksan settings
- "open cmd" → command prompt, cmd, terminal
- "open vs code" → vscode, vs code, buksan vscode
- "open word" → microsoft word, word, buksan word
- "open excel" → excel, buksan excel
- "open powerpoint" → powerpoint, buksan powerpoint
- "open teams" → teams, microsoft teams
- "open meet" → google meet, open meet, buksan meet
- "open camera" → camera, buksan camera
- "volume up" → taasan volume, louder, mas malakas
- "volume down" → babaan volume, quieter, mas mahina
- "mute" → i-mute, tahimik, wag maingay
- "unmute" → i-unmute, bukasin sound
- "brightness up" → taasan brightness, mas maliwanag
- "brightness down" → babaan brightness, mas madilim
- "screenshot" → screenshot, kumuha ng screenshot, i-screenshot
- "lock screen" → i-lock, lock screen
- "shutdown" → i-shutdown, patayin computer, turn off
- "restart" → i-restart, i-reboot
- "what time" → anong oras, what time, ilang na
- "what date" → anong petsa, what date, today, anong araw
- "battery" → battery, baterya
- "cpu usage" → cpu, processor
- "ram usage" → ram, memory
- "shutdown friday" → goodbye friday, shutdown friday, patayin friday
- "minimize all" → i-minimize lahat, show desktop
- "close window" → isara, close window
- "switch window" → alt tab, switch window, palitan window
- "search" → search for, hanapin, maghanap, can you search, search something for me, i need to search
- "set reminder" → remind me to, set a reminder, paalala, ipaalala, mag-reminder
- "list reminders" → show my reminders, list my reminders, tingnan reminders
- "add calendar event" → add event, add to calendar, schedule meeting, calendar event, mag-schedule, i-schedule, idagdag sa calendar
- "start air mouse" → start air mouse, enable air mouse, i-on air mouse
- "stop air mouse" → stop air mouse, disable air mouse, i-off air mouse
- "start sign launcher" → start sign launcher, enable sign language, i-on sign launcher
- "stop sign launcher" → stop sign launcher, disable sign language, i-off sign launcher

If command matched:
{
    "has_command": true,
    "command": "exact keyword or full sentence for reminders/calendar",
    "speak_response": "Short natural response. Like 'On it!' or 'Sure thing, sir.' Keep it brief."
}

SPECIAL NOTE FOR SCHEDULING / REMINDER COMMANDS:
- For reminders and calendar events, preserve the user's FULL details in "command"

If NO command — answer the question fully and naturally:
{
    "has_command": false,
    "command": null,
    "speak_response": "Give a complete, detailed answer. Be informative, conversational, and human."
}

RESPONSE STYLE:
- Always respond in Filipino/Tagalog or English depending on what the user used.
- Keep responses natural and conversational.

CRITICAL: Return ONLY valid JSON. No markdown. No backticks. No extra text.
"""


def _build_history_prompt() -> str:
    parts = []
    if _summary_memory:
        parts.append(f"\nSUMMARY OF PREVIOUS CONVERSATION:\n{_summary_memory}")
    if _conversation_history:
        parts.append("\nRECENT CONVERSATION:")
        for entry in _conversation_history:
            role = "User" if entry["role"] == "user" else "FRIDAY"
            parts.append(f"{role}: {entry['text']}")
    parts.append("\n(Use this context to answer the current message)")
    return "\n".join(parts)


def ask_local_ai(user_text: str) -> dict:
    """Ask local Ollama model with optional Tavily web search context."""
    try:
        if ollama_client is None:
            raise RuntimeError("ollama is not installed. Run: pip install ollama")

        web_context = _search_web(user_text)
        history_prompt = _build_history_prompt()

        if web_context:
            context_block = f"\n\nWEB SEARCH RESULTS (use this as reference):\n{web_context}"
        else:
            context_block = "\n\n(No internet search available — answer based on your knowledge. If unsure, say so honestly.)"

        full_prompt = f"{SYSTEM_PROMPT}{history_prompt}{context_block}\n\nUser said: \"{user_text}\""

        response = ollama_client.chat(
            model="qwen2.5:0.5b",
            messages=[{"role": "user", "content": full_prompt}],
        )

        text = response["message"]["content"].strip()
        logger.info("Local AI raw response: %s", text)

        text = re.sub(r"```json|```", "", text).strip()

        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            _conversation_history.append({"role": "user", "text": user_text})
            _conversation_history.append({"role": "friday", "text": result.get("speak_response", "")})
            return result

        _conversation_history.append({"role": "user", "text": user_text})
        _conversation_history.append({"role": "friday", "text": text})
        return {"has_command": False, "command": None, "speak_response": text}

    except Exception as e:
        logger.error("Local AI error: %s", e)
        return {"has_command": True, "command": user_text, "speak_response": ""}