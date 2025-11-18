"""
AI Functions Module for Assistant Agent

This module contains AI-related functions extracted from the AssistantAgent class:
- Agent resolution using AI reasoning
- Simple completions for quick AI tasks
- System prompt loading
- Agent function execution (the core AI function calling logic)
- Runbook examples retrieval

All functions take 'self' as the first parameter to maintain compatibility with the
original class methods.
"""

import json
import re
import os
import requests
import time


def _resolve_agent_with_ai(self, user_input: str, agents: list) -> str:
    """
    Use AI reasoning to resolve which agent the user meant.

    This function uses AI to match user input (which may contain typos, partial names,
    or role-based references) to the actual agent names available in the system.

    Args:
        self: The agent instance
        user_input: The user's input that needs to be resolved to an agent name
        agents: List of available agents with their metadata

    Returns:
        The resolved agent name, or None if no reasonable match exists
    """
    try:
        # Prepare agent information for AI
        agent_info = []
        for agent in agents:
            status = agent.get('status', 'unknown')
            name = agent.get('name', 'unknown')
            role = agent.get('role', 'N/A')
            agent_info.append(f"- {name} ({status}) - {role}")

        agent_list = "\n".join(agent_info)

        # Create a focused prompt for agent resolution
        prompt = f"""You are helping resolve which agent a user meant.

USER INPUT: "{user_input}"

AVAILABLE AGENTS:
{agent_list}

Analyze the user input and determine which agent they most likely meant. Consider:
- Typos and misspellings
- Partial names
- Phonetic similarities
- Role-based references

Respond with ONLY the exact agent name from the list above, or "NONE" if no reasonable match exists.

Examples:
- "lise" → "lisa"
- "calc" → "calculator"
- "research guy" → "researcher"
- "data person" → "data_analyst"
- "xyz123nonsense" → "NONE"

Agent name:"""

        # Use the same completion method as the main assistant
        response = _get_simple_completion(self, prompt)

        # Extract the agent name from response
        resolved_name = response.strip().lower()

        # Validate the resolved name exists in our agent list
        available_names = [agent['name'] for agent in agents]
        for name in available_names:
            if name.lower() == resolved_name:
                return name

        # If AI returned "NONE" or invalid name
        return None

    except Exception as e:
        print(f"[DEBUG] Error in AI agent resolution: {e}")
        return None


def _get_simple_completion(self, prompt: str) -> str:
    """
    Get a simple completion for agent resolution.

    This is a lightweight completion function optimized for quick, consistent
    responses like agent name resolution. Uses low temperature for deterministic results.

    Args:
        self: The agent instance
        prompt: The prompt to send to the AI

    Returns:
        The AI's response as a string, or "NONE" if an error occurs
    """
    try:
        messages = [{"role": "user", "content": prompt}]

        # Use the same client and model as main completion
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=50,
            temperature=0.1  # Low temperature for consistent results
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"[DEBUG] Error getting simple completion: {e}")
        return "NONE"


def _load_system_prompt_instructions(self) -> str:
    """
    Load system prompt instructions from the runbook.

    Reads the assistant.md runbook file and extracts the "System Prompt Instructions"
    section which contains special instructions for the AI system prompt.

    Args:
        self: The agent instance

    Returns:
        The system prompt instructions as a string, or empty string if not found
    """
    try:
        runbook_path = os.path.join(os.path.dirname(__file__), '..', '..', 'runbooks', 'assistant.md')

        if not os.path.exists(runbook_path):
            print(f"Warning: Runbook file not found at {runbook_path}")
            return ""

        with open(runbook_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract the System Prompt Instructions section
        pattern = r'## System Prompt Instructions\s*\n(.*?)(?=\n##|\Z)'
        match = re.search(pattern, content, re.DOTALL)

        if match:
            return match.group(1).strip()
        else:
            print("Warning: System Prompt Instructions section not found in runbook")
            return ""

    except Exception as e:
        print(f"Warning: Could not load system prompt instructions: {e}")
        return ""


def _execute_agent_function(self, function_name: str, function_args: str, reply_to: str) -> str:
    """
    Execute agent management functions like create_agent, delete_agent, manage_agents.

    This is the core AI function calling logic that handles all agent lifecycle operations.
    It processes function calls from the AI and executes the corresponding operations via
    the orchestrator API.

    Supported functions:
    - manage_agents: Start, stop, or restart agents
    - create_agent: Create a new agent with capabilities and optional tools
    - delete_agent: Delete an existing agent
    - smart_agent_operation: Smart agent operations with AI name resolution
    - get_agent_info: Get comprehensive agent information
    - get_runbook_examples: Get examples of existing runbooks
    - get_action_servers: List available MCP action servers
    - assign_action_server: Assign tools to an agent
    - remove_action_server: Remove tools from an agent

    Args:
        self: The agent instance
        function_name: Name of the function to execute
        function_args: JSON string containing function arguments
        reply_to: Topic to send responses to

    Returns:
        A formatted string with the result of the operation (success/error message)
    """
    try:
        if function_name == "manage_agents":
            # Parse the arguments
            args = json.loads(function_args)
            action = args.get("action")
            agent_name = args.get("agent_name")

            if action not in ["start", "stop", "restart"]:
                return f"❌ Invalid action '{action}'. Must be 'start', 'stop', or 'restart'."

            if not agent_name:
                return "❌ Agent name is required."

            # Normalize agent name to lowercase to match how agents are stored
            agent_name = agent_name.lower()

            print(f"[ASSISTANT] Executing manage_agents: {action} {agent_name}")

            # Call the orchestrator endpoint
            if action in ["start", "restart"]:
                response = requests.post(
                    f"{self.orchestrator_url}/agents/start",
                    json={"name": agent_name},
                    timeout=10
                )
            else:  # stop
                response = requests.post(
                    f"{self.orchestrator_url}/agents/stop",
                    json={"name": agent_name},
                    timeout=10
                )

            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    # Clear cache since agent state changed
                    self._clear_agents_cache()
                    return f"✅ Agent '{agent_name}' {action}ed successfully."
                else:
                    error_message = result.get('error', 'Unknown error')
                    if "is already running" in error_message and action == "start":
                        return f"ℹ️ Agent '{agent_name}' is already running."
                    return f"❌ Failed to {action} agent '{agent_name}': {error_message}"
            else:
                return f"❌ HTTP error {response.status_code} when trying to {action} agent '{agent_name}'"

        elif function_name == "create_agent":
            # Parse the arguments
            args = json.loads(function_args)
            agent_name = args.get("name")
            role = args.get("role")
            capabilities = args.get("capabilities", [])
            action_server = args.get("action_server")  # Optional

            if not agent_name or not role:
                return "❌ Agent name and role are required."

            # Normalize agent name to lowercase to match how agents are stored
            agent_name = agent_name.lower()

            if not capabilities:
                return "❌ At least one capability is required."

            print(f"[ASSISTANT] Executing create_agent: {agent_name} with {len(capabilities)} capabilities")
            if action_server:
                print(f"[ASSISTANT] Assigning action server: {action_server}")

            # Call the orchestrator create endpoint
            payload = {
                "name": agent_name,
                "role": role,
                "capabilities": capabilities
            }
            if action_server:
                payload["action_server"] = action_server

            response = requests.post(
                f"{self.orchestrator_url}/agents/create",
                json=payload,
                timeout=15
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    # Clear cache since new agent was added
                    self._clear_agents_cache()
                    message = f"🎉 Successfully created agent '{agent_name}' and started it!\n\nThe agent has been configured with the following capabilities:\n" + "\n".join([f"• {cap.get('name', 'Unknown')}" for cap in capabilities])

                    if result.get("action_server_assigned"):
                        message += f"\n\n🔧 Tools assigned: {action_server}"

                    return message
                else:
                    return f"❌ Failed to create agent '{agent_name}': {result.get('error', 'Unknown error')}"
            else:
                return f"❌ HTTP error {response.status_code} when creating agent '{agent_name}'"

        elif function_name == "delete_agent":
            # Parse the arguments
            args = json.loads(function_args)
            agent_name = args.get("name")
            remove_runbook = args.get("remove_runbook", False)

            if not agent_name:
                return "❌ Agent name is required."

            # Normalize agent name to lowercase to match how agents are stored
            agent_name = agent_name.lower()

            print(f"[ASSISTANT] Executing delete_agent: {agent_name} (remove_runbook: {remove_runbook})")

            # Call the orchestrator delete endpoint
            response = requests.post(
                f"{self.orchestrator_url}/agents/delete",
                json={
                    "name": agent_name,
                    "remove_runbook": remove_runbook
                },
                timeout=15
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    # Clear cache since agent was removed
                    self._clear_agents_cache()
                    message = f"✅ Successfully deleted agent '{agent_name}'"
                    if result.get("runbook_removed"):
                        message += " and removed its runbook."
                    else:
                        message += " (runbook preserved)."
                    return message
                else:
                    return f"❌ Failed to delete agent '{agent_name}': {result.get('error', 'Unknown error')}"
            else:
                return f"❌ HTTP error {response.status_code} when deleting agent '{agent_name}'"

        elif function_name == "smart_agent_operation":
            # Parse the arguments
            args = json.loads(function_args)
            action = args.get("action")
            agent_name = args.get("agent_name")

            if action not in ["start", "stop", "delete"]:
                return f"❌ Invalid action '{action}'. Must be 'start', 'stop', or 'delete'."

            if not agent_name:
                return "❌ Agent name is required."

            print(f"[ASSISTANT] Executing smart_agent_operation: {action} {agent_name}")
            return self.smart_agent_operation(action, agent_name, reply_to)

        elif function_name == "get_agent_info":
            print(f"[ASSISTANT] Executing get_agent_info")
            return self.get_agent_info(reply_to)

        elif function_name == "get_runbook_examples":
            print(f"[ASSISTANT] Executing get_runbook_examples")
            return _get_runbook_examples(self)

        elif function_name == "get_action_servers":
            print(f"[ASSISTANT] Executing get_action_servers")
            # Call the orchestrator to get available action servers
            response = requests.get(
                f"{self.orchestrator_url}/action-servers/available",
                timeout=15
            )

            if response.status_code == 200:
                result = response.json()
                servers = result.get("servers", [])

                if not servers:
                    return "ℹ️ No action servers are currently configured."

                message = "Available MCP Action Servers:\n\n"
                for server in servers:
                    message += f"• **{server.get('id')}** - {server.get('description', 'No description')}\n"
                    message += f"  Type: {server.get('type', 'unknown')}\n\n"

                return message
            else:
                return f"❌ Failed to get action servers (HTTP {response.status_code})"

        elif function_name == "assign_action_server":
            args = json.loads(function_args)
            agent_name = args.get("agent_name")
            action_server = args.get("action_server")

            if not agent_name or not action_server:
                return "❌ Both agent_name and action_server are required."

            agent_name = agent_name.lower()
            print(f"[ASSISTANT] Executing assign_action_server: {agent_name} -> {action_server}")

            response = requests.post(
                f"{self.orchestrator_url}/agents/assign-action-server",
                json={
                    "agent_name": agent_name,
                    "action_server": action_server
                },
                timeout=15
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    message = f"✅ {result.get('message')}"
                    if result.get("agent_restarted"):
                        message += "\n🔄 Agent restarted - tools are now active!"
                    else:
                        message += f"\n\nℹ️ {result.get('note', '')}"
                    return message
                else:
                    return f"❌ {result.get('error', 'Unknown error')}"
            else:
                return f"❌ HTTP error {response.status_code}"

        elif function_name == "remove_action_server":
            args = json.loads(function_args)
            agent_name = args.get("agent_name")

            if not agent_name:
                return "❌ Agent name is required."

            agent_name = agent_name.lower()
            print(f"[ASSISTANT] Executing remove_action_server: {agent_name}")

            response = requests.post(
                f"{self.orchestrator_url}/agents/remove-action-server",
                json={"agent_name": agent_name},
                timeout=15
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    return f"✅ {result.get('message')}\n\nℹ️ {result.get('note', '')}"
                else:
                    return f"❌ {result.get('error', 'Unknown error')}"
            else:
                return f"❌ HTTP error {response.status_code}"

        else:
            return f"❌ Unknown function '{function_name}'"

    except json.JSONDecodeError as e:
        return f"❌ Failed to parse function arguments: {str(e)}"
    except requests.RequestException as e:
        return f"❌ Network error when calling orchestrator: {str(e)}"
    except Exception as e:
        return f"❌ Unexpected error executing {function_name}: {str(e)}"


def _get_runbook_examples(self) -> str:
    """
    Get examples of existing agent runbooks with job titles and structures.

    Fetches all available runbooks from the orchestrator and formats them as examples
    to help users understand the runbook structure and naming conventions.

    Args:
        self: The agent instance

    Returns:
        A formatted string containing runbook examples and best practices
    """
    try:
        response = requests.get("http://localhost:9000/agents/runbooks")
        if response.status_code != 200:
            return "❌ Could not retrieve runbook examples"

        runbooks = response.json()
        if not runbooks:
            return "📚 No existing runbooks found"

        examples = []
        examples.append("📚 **Existing Agent Runbook Examples:**\n")

        for runbook in runbooks:
            name = runbook.get('agent_name', 'Unknown')
            job_title = runbook.get('job_title', 'N/A')
            role = runbook.get('role', 'N/A')
            capabilities = runbook.get('capabilities', [])

            examples.append(f"**{name.title()}:**")
            examples.append(f"  • Job Title: \"{job_title}\"")
            examples.append(f"  • Role: {role[:80]}{'...' if len(role) > 80 else ''}")
            examples.append(f"  • Capabilities: {len(capabilities)} defined")
            examples.append("")

        examples.append("**Best Practices:**")
        examples.append("• Job Title: 2-3 words, professional (e.g., \"Data Analyst\", \"Tax Expert\")")
        examples.append("• Role: Detailed description for context")
        examples.append("• Include ## Job Title section in runbook markdown")
        examples.append("• Avoid generic \"AI Agent\" - be domain-specific")

        return "\n".join(examples)

    except Exception as e:
        return f"❌ Error retrieving runbook examples: {str(e)}"
