"""
AI Router — 3 modes:

  general  → Gemini API — CONVERSATION ONLY, no system commands
  search   → Tavily + Ollama — SEARCH ONLY, no system commands
  command  → Direct command match ONLY — open youtube, volume up, etc.
             No AI brain, purely routes to actions.py
"""

import logging
import os
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Shared state
# ─────────────────────────────────────────────
_ai_mode: str = "general"
_is_searching: bool = False


def get_ai_mode() -> str:
    return _ai_mode


def is_searching() -> bool:
    return _is_searching


def set_ai_mode(mode: str) -> None:
    global _ai_mode
    if mode not in ("general", "search", "command"):
        raise ValueError(f"Invalid AI mode: {mode}. Use 'general', 'search', or 'command'.")
    _ai_mode = mode
    logger.info("AI mode switched to: %s", _ai_mode)


# ─────────────────────────────────────────────
# General AI — Gemini
# Pure conversation only — no command execution
# ─────────────────────────────────────────────
def _ask_general(command: str) -> dict:
    try:
        from app.services.gemini_service import ask_gemini
        result = ask_gemini(command)
        # Strip any command — General AI is conversation ONLY
        return {
            "has_command": False,
            "command": None,
            "speak_response": result.get("speak_response", ""),
            "mode": "general",
        }
    except Exception as e:
        logger.error("General AI error: %s", e)
        return {
            "has_command": False,
            "command": None,
            "speak_response": "Sorry sir, I'm having trouble connecting to Gemini right now.",
            "mode": "general",
        }


# ─────────────────────────────────────────────
# Search AI — Tavily + Ollama
# Pure search/conversation — no command execution
# ─────────────────────────────────────────────
def _ask_search(command: str) -> dict:
    global _is_searching
    _is_searching = True
    try:
        # Step 1 — Tavily web search
        web_context = _search_web(command)

        # Step 2 — Ollama summarizes the results
        try:
            import ollama as ollama_client

            if web_context:
                prompt = f"""You are FRIDAY, a helpful AI assistant.
Using the web search results below, answer the user's question clearly and concisely.
Respond in the same language the user used (Filipino or English).

WEB SEARCH RESULTS:
{web_context}

User asked: "{command}"

Respond naturally and conversationally. Keep it brief."""
            else:
                prompt = f"""You are FRIDAY, a helpful AI assistant.
Answer this question based on your knowledge. Be honest if you're not sure.
Respond in the same language the user used (Filipino or English).

User asked: "{command}" """

            response = ollama_client.chat(
                model="qwen2.5:0.5b",
                messages=[{"role": "user", "content": prompt}],
            )
            answer = response["message"]["content"].strip()

        except Exception as e:
            logger.error("Ollama error in search mode: %s", e)
            answer = web_context[:400] + "..." if web_context else "Sorry sir, I couldn't find any results for that."

        return {
            "has_command": False,
            "command": None,
            "speak_response": answer,
            "search_context": web_context,
            "mode": "search",
        }
    finally:
        _is_searching = False


def _search_web(query: str) -> str:
    """Search the web using Tavily."""
    try:
        from tavily import TavilyClient
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            logger.warning("TAVILY_API_KEY not set.")
            return ""
        client = TavilyClient(api_key=api_key)
        results = client.search(query, max_results=3)
        parts = [r.get("content", "").strip() for r in results.get("results", []) if r.get("content")]
        return "\n\n".join(parts[:3])
    except Exception as e:
        logger.warning("Tavily search failed: %s", e)
        return ""


# ─────────────────────────────────────────────
# Command AI — Direct match only
# No AI brain — purely maps to actions.py
# This is the ONLY mode that executes system commands
# ─────────────────────────────────────────────
def _ask_command(command: str) -> dict:
    from app.services.actions import COMMANDS

    command_lower = command.lower().strip()

    # Check direct command map (longest match first)
    sorted_commands = sorted(COMMANDS.items(), key=lambda x: len(x[0]), reverse=True)
    for keyword, _ in sorted_commands:
        if keyword in command_lower:
            return {
                "has_command": True,
                "command": keyword,
                "speak_response": "",
                "mode": "command",
            }

    # Check search/play patterns
    search_keywords = ["search", "play", "look up", "youtube search"]
    if any(k in command_lower for k in search_keywords):
        return {
            "has_command": True,
            "command": command,
            "speak_response": "",
            "mode": "command",
        }

    # Reminder patterns
    reminder_keywords = ["remind me", "ipaalala", "mag-reminder", "list reminders"]
    if any(k in command_lower for k in reminder_keywords):
        return {
            "has_command": True,
            "command": command,
            "speak_response": "",
            "mode": "command",
        }

    # Calendar patterns
    calendar_keywords = ["add event", "schedule", "mag-schedule", "i-schedule", "idagdag sa calendar"]
    if any(k in command_lower for k in calendar_keywords):
        return {
            "has_command": True,
            "command": command,
            "speak_response": "",
            "mode": "command",
        }

    # No match
    return {
        "has_command": False,
        "command": None,
        "speak_response": "Sorry sir, command not recognized. Please try Command AI mode for system commands.",
        "mode": "command",
    }


# ─────────────────────────────────────────────
# Main Router
# ─────────────────────────────────────────────
def ask_ai(command: str) -> dict:
    """Route command to the selected AI brain."""
    logger.info("ask_ai: mode=%s command=%s", _ai_mode, command)

    if _ai_mode == "search":
        return _ask_search(command)
    elif _ai_mode == "command":
        return _ask_command(command)
    else:
        # general — Gemini, conversation only
        return _ask_general(command)