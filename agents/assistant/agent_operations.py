"""
Agent Operations Module

This module contains standalone functions for managing agents in the AI agents system.
These functions handle agent lifecycle operations (start, stop, delete), agent discovery,
and intelligent agent management operations.

All functions take 'self' as the first parameter to maintain compatibility with
the original class-based implementation where these were methods.
"""

import json
import time
import requests


def discover_all_agents(self):
    """
    Query the orchestrator for ALL agents (running or not) and their capabilities.

    Uses caching to reduce API calls. Cache is valid for 60 seconds.

    Args:
        self: The agent instance (for accessing cache attributes)

    Returns:
        list: List of dictionaries containing agent information including:
            - name: Agent name
            - role: Agent role description
            - capabilities: List of capability names
            - is_running: Boolean indicating if agent is running
            - status: 'running' or 'stopped'
            - actions: List of available actions for the agent
    """
    # Check if we have cached data that's still fresh (60 seconds - increased cache time)
    current_time = time.time()
    if hasattr(self, '_agents_cache') and hasattr(self, '_agents_cache_time'):
        if current_time - self._agents_cache_time < 60:  # Cache for 60 seconds
            # Use cached data silently (no debug message to reduce noise)
            return self._agents_cache

    try:
        print(f"[DEBUG] Fetching fresh agent data from orchestrator...")

        # Get all runbooks - this gives us info about all agents, not just running ones
        runbooks_response = requests.get("http://localhost:9000/agents/runbooks")
        if runbooks_response.status_code != 200:
            print(f"[ASSISTANT] Failed to get runbooks: {runbooks_response.status_code}")
            return []

        runbooks_data = runbooks_response.json()

        # Get current running status
        running_response = requests.get("http://localhost:9000/agents")
        running_agents = []
        if running_response.status_code == 200:
            running_data = running_response.json()
            running_agents = [agent['name'] for agent in running_data if agent.get('status') == 'running']

        # Get all agent actions
        actions_response = requests.get("http://localhost:9000/actions/all")
        agent_actions_map = {}
        if actions_response.status_code == 200:
            actions_data = actions_response.json()
            # Build a map of agent_name -> list of actions
            for action_item in actions_data.get('actions', []):
                agent_name = action_item.get('agent_name')
                action = action_item.get('action')
                if agent_name not in agent_actions_map:
                    agent_actions_map[agent_name] = []
                agent_actions_map[agent_name].append(action)

        # Build comprehensive agent information
        agents_info = []
        for runbook in runbooks_data:
            agent_name = runbook.get('agent_name', '')
            if agent_name == "assistant":  # Skip self
                continue

            agent_info = {
                'name': agent_name,
                'role': runbook.get('role', 'Unknown role'),
                'capabilities': [cap.get('name', 'Unknown') for cap in runbook.get('capabilities', [])],
                'is_running': agent_name in running_agents,
                'status': 'running' if agent_name in running_agents else 'stopped',
                'actions': agent_actions_map.get(agent_name, [])
            }
            agents_info.append(agent_info)

        # Cache the results
        self._agents_cache = agents_info
        self._agents_cache_time = current_time

        # Count total actions
        total_actions = sum(len(agent.get('actions', [])) for agent in agents_info)
        print(f"[ASSISTANT] Discovered {len(agents_info)} agents with {total_actions} total actions (cached)")
        return agents_info

    except Exception as e:
        print(f"Error discovering all agents: {e}")
        return []


def _clear_agents_cache(self):
    """
    Clear the cached agent data to force fresh fetch on next request.

    This should be called whenever agent state changes (start, stop, create, delete)
    to ensure the cache is invalidated.

    Args:
        self: The agent instance (for accessing cache attributes)
    """
    if hasattr(self, '_agents_cache'):
        delattr(self, '_agents_cache')
    if hasattr(self, '_agents_cache_time'):
        delattr(self, '_agents_cache_time')


def start_agent(self, agent_name: str) -> bool:
    """
    Start an agent if it's not already running.

    Makes a POST request to the orchestrator to start the specified agent.

    Args:
        self: The agent instance
        agent_name: Name of the agent to start

    Returns:
        bool: True if the agent was started successfully, False otherwise
    """
    try:
        response = requests.post("http://localhost:9000/agents/start",
                               json={"name": agent_name})
        if response.status_code == 200:
            result = response.json()
            return result.get('ok', False)
        return False
    except Exception as e:
        print(f"Error starting agent {agent_name}: {e}")
        return False


def stop_agent(self, agent_name: str) -> bool:
    """
    Stop an agent if it's currently running.

    Makes a POST request to the orchestrator to stop the specified agent.

    Args:
        self: The agent instance
        agent_name: Name of the agent to stop

    Returns:
        bool: True if the agent was stopped successfully, False otherwise
    """
    try:
        response = requests.post("http://localhost:9000/agents/stop",
                               json={"name": agent_name})
        if response.status_code == 200:
            result = response.json()
            return result.get('ok', False)
        return False
    except Exception as e:
        print(f"Error stopping agent {agent_name}: {e}")
        return False


def _handle_agent_management_command(self, command_string: str, reply_to: str):
    """
    Handle direct agent management commands like start/stop/restart agents.

    Parses a command string and executes the requested action on one or more agents.
    Sends progress updates and results back to the user via the reply_to topic.

    Args:
        self: The agent instance (for accessing discover_all_agents, start_agent, etc.)
        command_string: Command string like "start all agents" or "stop bob agents"
        reply_to: NATS topic to send responses to (usually "user_session:main")

    Command Format:
        <action> <target> agents
        - action: start, stop, or restart
        - target: all, or specific agent name

    Examples:
        - "start all agents" - starts all stopped agents
        - "stop bob agents" - stops the bob agent
        - "restart all agents" - restarts all agents
    """
    message_lower = command_string.lower()

    # Parse the command string to extract action and target
    parts = command_string.lower().split()
    if len(parts) < 3:
        self.send_message(reply_to, "❓ Invalid agent management command format.")
        return

    action = parts[0]  # start/stop/restart
    target = parts[1]  # all/specific agent name

    # Validate action
    if action not in ['start', 'stop', 'restart']:
        self.send_message(reply_to, f"❓ Unknown action '{action}'. Use start, stop, or restart.")
        return

    # Get all agents info
    agents_info = discover_all_agents(self)
    if not agents_info:
        self.send_message(reply_to, "❌ Unable to discover available agents.")
        return

    # Set up action-specific variables
    if action == 'start':
        action_verb = 'Starting'
        success_emoji = '✅'
        fail_emoji = '❌'
    elif action == 'stop':
        action_verb = 'Stopping'
        success_emoji = '✅'
        fail_emoji = '❌'
    elif action == 'restart':
        action_verb = 'Restarting'
        success_emoji = '🔄'
        fail_emoji = '❌'

    # Filter agents based on target
    if target.lower() == 'all':
        target_agents = [agent for agent in agents_info if agent['name'] != 'assistant']
    else:
        # Find specific agent
        target_agents = [agent for agent in agents_info if agent['name'].lower() == target.lower() and agent['name'] != 'assistant']

    if not target_agents:
        self.send_message(reply_to, f"❌ Agent '{target}' not found or not available for management.")
        return

    # Filter out agents that are already in the desired state
    if action == 'start':
        agents_to_process = [agent for agent in target_agents if not agent.get('is_running', False)]
    elif action == 'stop':
        agents_to_process = [agent for agent in target_agents if agent.get('is_running', False)]
    else:  # restart
        agents_to_process = target_agents

    if not agents_to_process:
        status_word = "running" if action == 'start' else "stopped"
        self.send_message(reply_to, f"ℹ️ All target agents are already {status_word}.")
        return

    self.send_message(reply_to, f"🚀 {action_verb} {len(agents_to_process)} agent(s): {', '.join([a['name'] for a in agents_to_process])}")

    results = []
    for agent in agents_to_process:
        agent_name = agent['name']
        self.send_message(reply_to, f"⚙️ {action_verb} {agent_name}...")

        if action == 'restart':
            # For restart, stop first then start
            stop_success = stop_agent(self, agent_name)
            if stop_success:
                start_success = start_agent(self, agent_name)
                success = start_success
            else:
                success = False
        elif action == 'start':
            success = start_agent(self, agent_name)
        elif action == 'stop':
            success = stop_agent(self, agent_name)

        if success:
            results.append(f"{success_emoji} {agent_name}")
            self.send_message(reply_to, f"{success_emoji} {agent_name} {action}ed successfully")
        else:
            results.append(f"{fail_emoji} {agent_name}")
            self.send_message(reply_to, f"{fail_emoji} Failed to {action} {agent_name}")

    # Summary
    successful = len([r for r in results if success_emoji in r])
    total = len(results)
    self.send_message(reply_to, f"📊 {action.title()} complete: {successful}/{total} agents successful")


def manage_agents(self, action: str, target: str = "all", reply_to: str = None):
    """
    Manage agents - can be called by AI when users request agent management.

    This is a convenience wrapper around _handle_agent_management_command that
    provides a simpler function signature for use in AI function calling.

    Args:
        self: The agent instance
        action: Action to perform (start, stop, restart)
        target: Target agents ('all' or specific agent name)
        reply_to: NATS topic to send responses to (defaults to "user_session:main")

    Returns:
        The result of _handle_agent_management_command
    """
    return _handle_agent_management_command(self, f"{action} {target} agents", reply_to or "user_session:main")


def smart_agent_operation(self, action: str, agent_name: str, reply_to: str = None):
    """
    Smart agent operations using AI reasoning to resolve agent names.

    This function provides intelligent agent name resolution, handling typos,
    partial names, and other variations. It can perform start, stop, and delete
    operations on agents.

    Args:
        self: The agent instance (for accessing _resolve_agent_with_ai, etc.)
        action: Action to perform ('start', 'stop', or 'delete')
        agent_name: Name or partial name of the agent (will be resolved)
        reply_to: NATS topic to send responses to (defaults to "user_session:main")

    Returns:
        str: Status message describing the result of the operation

    Examples:
        - smart_agent_operation(self, "start", "bob", reply_to)
        - smart_agent_operation(self, "stop", "researcher", reply_to)
        - smart_agent_operation(self, "delete", "old_agent", reply_to)
    """
    try:
        # Get current agent information
        response = requests.get("http://localhost:9000/agents")
        if response.status_code != 200:
            return f"❌ Could not get agent list to resolve '{agent_name}'"

        agents = response.json()
        available_names = [agent['name'] for agent in agents]

        # Try exact match first (case insensitive)
        exact_match = next((name for name in available_names if name.lower() == agent_name.lower()), None)
        if exact_match:
            resolved_name = exact_match
        else:
            # Use AI reasoning to resolve the agent name
            resolved_name = self._resolve_agent_with_ai(agent_name, agents)
            if resolved_name is None:
                return f"❌ No agent found matching '{agent_name}'. Available agents: {', '.join(available_names)}"

        # Perform the action with resolved name
        if action == "start":
            result = _handle_agent_management_command(self, f"start {resolved_name}", reply_to or "user_session:main")
            if resolved_name != agent_name:
                return f"🔍 Resolved '{agent_name}' to '{resolved_name}'\n{result}"
            return result
        elif action == "stop":
            result = _handle_agent_management_command(self, f"stop {resolved_name}", reply_to or "user_session:main")
            if resolved_name != agent_name:
                return f"🔍 Resolved '{agent_name}' to '{resolved_name}'\n{result}"
            return result
        elif action == "delete":
            try:
                # Use the proper delete endpoint with remove_runbook option
                delete_response = requests.post(
                    f"http://localhost:9000/agents/delete",
                    json={
                        "name": resolved_name,
                        "remove_runbook": True  # Always try to remove runbook for smart operations
                    },
                    timeout=15
                )

                if delete_response.status_code == 200:
                    delete_result = delete_response.json()
                    if delete_result.get("ok"):
                        result = f"✅ Agent '{resolved_name}' deleted successfully"
                        if delete_result.get("runbook_removed"):
                            result += " (including runbook)"
                        result += "."
                    else:
                        error_msg = delete_result.get('error', 'Unknown error')
                        result = f"❌ Failed to delete agent '{resolved_name}': {error_msg}"
                else:
                    result = f"❌ HTTP error {delete_response.status_code} when deleting agent '{resolved_name}'"

                if resolved_name != agent_name:
                    return f"🔍 Resolved '{agent_name}' to '{resolved_name}'\n{result}"
                return result
            except Exception as e:
                return f"❌ Failed to delete agent '{resolved_name}': {str(e)}"

    except Exception as e:
        return f"❌ Error in smart agent operation: {str(e)}"


def get_agent_info(self, reply_to: str = None):
    """
    Get comprehensive agent information for AI decision making.

    Retrieves information about all agents including their status, roles,
    capabilities, and descriptions. Formats the information for both user
    display and AI reasoning.

    Args:
        self: The agent instance
        reply_to: NATS topic to send responses to (optional, not currently used)

    Returns:
        str: Formatted string with comprehensive agent information including:
            - Running agents with their roles and capabilities
            - Stopped agents with their roles and capabilities
            - Total agent count

    Example output:
        📊 **Agent Status Overview:**

        🟢 **Running Agents (2):**
          • **bob**: Email Assistant - email_read, email_send, email_search
          • **researcher**: Research Specialist - web_search, summarize

        ⚪ **Stopped Agents (1):**
          • **translator**: Language Translator - translate_text

        📈 **Total agents:** 3
    """
    try:
        # Get agent status
        response = requests.get("http://localhost:9000/agents")
        if response.status_code != 200:
            return "❌ Could not retrieve agent information"

        agents = response.json()

        # Get agent runbooks for capabilities
        runbooks_dict = {}
        try:
            runbook_response = requests.get("http://localhost:9000/agents/runbooks")
            if runbook_response.status_code == 200:
                runbooks_list = runbook_response.json()
                # Convert list to dictionary keyed by agent_name
                for runbook in runbooks_list:
                    agent_name = runbook.get('agent_name')
                    if agent_name:
                        runbooks_dict[agent_name] = runbook
        except Exception as e:
            print(f"[ASSISTANT] Warning: Failed to load runbooks: {e}")
            pass

        # Build comprehensive agent information
        agent_details = []
        for agent in agents:
            name = agent.get('name', 'unknown')
            status = agent.get('status', 'unknown')
            role = agent.get('role', 'N/A')

            # Get capabilities from runbooks if available
            runbook_info = runbooks_dict.get(name, {})
            capabilities = runbook_info.get('capabilities', [])
            # Extract just the capability names for brevity
            capability_names = [cap.get('name', '') for cap in capabilities if isinstance(cap, dict)]
            description = runbook_info.get('role', 'No description available')  # Use role from runbook

            agent_info = {
                'name': name,
                'status': status,
                'role': role,
                'description': description,
                'capabilities': capability_names[:3] if capability_names else []  # Limit to first 3 for brevity
            }
            agent_details.append(agent_info)

        # Format for both user display and AI reasoning
        running_agents = [a for a in agent_details if a['status'] == 'running']
        stopped_agents = [a for a in agent_details if a['status'] != 'running']

        # Create user-friendly display
        result = f"📊 **Agent Status Overview:**\n\n"

        if running_agents:
            result += f"🟢 **Running Agents ({len(running_agents)}):**\n"
            for agent in running_agents:
                caps_text = f" - {', '.join(agent['capabilities'])}" if agent['capabilities'] else ""
                result += f"  • **{agent['name']}**: {agent['role']}{caps_text}\n"
            result += "\n"

        if stopped_agents:
            result += f"⚪ **Stopped Agents ({len(stopped_agents)}):**\n"
            for agent in stopped_agents:
                caps_text = f" - {', '.join(agent['capabilities'])}" if agent['capabilities'] else ""
                result += f"  • **{agent['name']}**: {agent['role']}{caps_text}\n"

        result += f"\n📈 **Total agents:** {len(agents)}"

        return result

    except Exception as e:
        return f"❌ Error getting agent info: {str(e)}"
