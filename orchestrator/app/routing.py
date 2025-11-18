"""Message routing and @mention extraction."""
import re
from typing import Tuple, List
from fastapi import WebSocket
from sqlalchemy.orm import Session
from . import models
from .database import SessionLocal


def extract_mentions(message: str) -> Tuple[List[str], str]:
    """
    Extract ALL @mentions from message (supports multi-agent routing).
    Filters out email addresses and validates against registered agents.

    Args:
        message: User message that may contain one or more @agentname mentions

    Returns:
        Tuple of (agent_names, cleaned_message)
        - agent_names: List of mentioned agent names (empty if no mentions)
        - cleaned_message: Message with @mentions removed

    Examples:
        "@bob introduce yourself" -> (["bob"], "introduce yourself")
        "@translator @bob hello" -> (["translator", "bob"], "hello")
        "hey @agent1 @agent2 do something" -> (["agent1", "agent2"], "hey do something")
        "send to user@example.com" -> ([], "send to user@example.com")
        "hello" -> ([], "hello")
    """
    # Pattern: @agentname (word boundary before @, word characters only, not followed by domain)
    # Negative lookbehind: not preceded by word character (avoids email addresses)
    # Negative lookahead: not followed by .domain (avoids @example.com)
    pattern = r'(?<!\w)@(\w+)(?!\.)'
    matches = re.findall(pattern, message)

    if matches:
        print(f"  🔍 extract_mentions raw regex matches: {matches}")
        print(f"     From message: {message[:150]}...")

        # Get list of registered agents to validate mentions
        db = SessionLocal()
        try:
            registered_agents = {agent.name.lower() for agent in db.query(models.Agent).all()}
            print(f"     Registered agents: {registered_agents}")
        finally:
            db.close()

        # Extract all unique agent names (preserve order, remove duplicates)
        # Only include names that correspond to registered agents
        agent_names = []
        for name in matches:
            name_lower = name.lower()
            if name_lower not in agent_names and name_lower in registered_agents:
                agent_names.append(name_lower)
                print(f"     ✅ Valid agent mention: {name_lower}")
            else:
                print(f"     ❌ Ignoring invalid/non-existent mention: {name_lower}")

        if agent_names:
            # Remove only valid @mentions from the message
            # Build pattern that only matches valid agent names
            valid_pattern = r'(?<!\w)@(?:' + '|'.join(re.escape(name) for name in agent_names) + r')(?!\.)'
            cleaned_message = re.sub(valid_pattern, '', message, flags=re.IGNORECASE).strip()
            return agent_names, cleaned_message

    return [], message


async def send_assistant_introduction(websocket: WebSocket, session_id: str, agent_runbooks: dict, running_processes: dict):
    """Send assistant introduction with capabilities when a new conversation starts."""
    try:
        # Check if assistant is actually running
        assistant_running = "assistant" in running_processes
        assistant_registered = agent_runbooks.get("assistant") is not None

        if not assistant_running:
            print(f"⚠️  Assistant agent is not running, skipping introduction")
            if assistant_registered:
                await websocket.send_text("🤖 Assistant agent is currently offline. Please start the assistant agent to begin our conversation.\n")
            else:
                await websocket.send_text("🤖 No assistant agent available. Please ensure the assistant agent is running.\n")
            return

        # Get assistant runbook
        assistant_runbook = agent_runbooks.get("assistant")
        if not assistant_runbook:
            print(f"⚠️  Assistant runbook not found, sending generic introduction")
            introduction = "🤖 Hello! I'm your AI assistant. I'm here to help with various tasks and can coordinate with other specialized agents when needed."
            await websocket.send_text(introduction + "\n")
            return

        # Build introduction message - simple greeting for user only
        role = assistant_runbook.get("role", "AI assistant")

        # Simple greeting for the user - detailed capabilities are for AI processing only
        introduction = f"🤖 Hello! I'm your {role}.\n\n"
        introduction += "Feel free to ask me anything or request complex tasks that I can help with!"

        # Note: Detailed capabilities are available to the AI in system prompts but not shown to user

        # Send the introduction message
        await websocket.send_text(introduction + "\n")
        print(f"📋 Sent assistant introduction for session '{session_id}' - Assistant is running and ready")

    except Exception as e:
        print(f"⚠️  Error sending assistant introduction: {e}")
        # Send a simple fallback introduction
        fallback_intro = "🤖 Hello! I'm your AI assistant. I'm here to help with various tasks."
        await websocket.send_text(fallback_intro + "\n")
