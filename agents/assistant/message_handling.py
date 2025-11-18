"""
Message handling module for the Assistant agent.

This module contains all message processing, AI chat responses, function calling,
and message routing logic extracted from the main AssistantAgent class.
"""

import json
import time
import re


def _message_handler(self, message: dict):
    """
    Handles an incoming user prompt with intelligent task routing and collaboration.

    Args:
        self: Reference to the AssistantAgent instance
        message: The incoming message dictionary containing parsed data
    """
    try:
        # Use the parsed data from the base class, with fallback parsing
        data = message.get('parsed_data')
        if data is None:
            # Fallback to manual parsing
            import json
            raw_data = message['data'].decode()
            try:
                data = json.loads(raw_data)
                print(f"[DEBUG] Manually parsed JSON message: {type(data)}", flush=True)
            except json.JSONDecodeError:
                data = raw_data
                print(f"[DEBUG] Message is plain text: {type(data)}", flush=True)

        # Check if this is a delegation response from another agent
        if isinstance(data, dict) and "from_agent" in data and "task_result" in data:
            self._handle_agent_response(data)
            return

        # Check if this is a natural conversation response from another agent
        # These are informational - the agent already sent the response to user_session
        # so we can safely ignore them to avoid duplicate processing
        if isinstance(data, dict) and "from_agent" in data and "collaboration_type" in data:
            if data.get("collaboration_type") == "natural_conversation_response":
                # Agent already sent response to user, no need to process
                print(f"[ASSISTANT] Received natural conversation response from {data.get('from_agent')} - already sent to user", flush=True)
                return

        # Handle regular user messages
        if isinstance(data, dict):
            messages = data.get("messages")
            reply_to = data.get("reply_to")
        else:
            # Plain text message - create message structure
            messages = [{"role": "user", "content": str(data)}]
            reply_to = "user_session:main"

        if not messages or not reply_to:
            print("Missing 'messages' or 'reply_to' in message.", flush=True)
            return

        # Get the user's latest message
        user_message = messages[-1]["content"] if messages else ""

        # Let the AI decide whether to handle directly or use collaboration
        # based on natural language understanding from the runbook
        _handle_direct_response(self, messages, reply_to)

    except json.JSONDecodeError:
        print(f"Could not decode incoming message: {message['data']}", flush=True)
    except Exception as e:
        print(f"An error occurred: {e}", flush=True)


def _enhance_messages_with_agent_history(self, messages):
    """
    Enhance the message list with relevant agent conversation history.

    Args:
        self: Reference to the AssistantAgent instance
        messages: List of message dictionaries to enhance

    Returns:
        Enhanced list of messages with conversation history added as system messages
    """
    if not hasattr(self, 'agent_conversations') or not self.agent_conversations:
        return messages

    # Create a copy of the original messages
    enhanced_messages = messages.copy()

    # Add conversation history with agents as system messages
    for agent_name, conversation in self.agent_conversations.items():
        if conversation:  # Only include agents with conversation history
            # Format the conversation history as a system message
            history_text = f"Previous conversation with {agent_name}:\n"
            for msg in conversation[-5:]:  # Include last 5 messages to avoid token limits
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                history_text += f"{role.title()}: {content}\n"

            enhanced_messages.insert(0, {
                "role": "system",
                "content": history_text.strip()
            })

    return enhanced_messages


def _handle_direct_response(self, messages, reply_to):
    """
    Handle simple tasks with direct AI response using runbook capabilities.

    This is the core message handling method that processes user messages through
    the AI chat completion system with OpenAI function calling support. It handles:
    - Agent discovery and action mapping
    - System prompt construction
    - Function call definitions for agent management
    - Streaming response processing
    - Function execution for agent lifecycle operations
    - Agent task routing via @mentions

    Args:
        self: Reference to the AssistantAgent instance
        messages: List of message dictionaries in OpenAI format
        reply_to: Topic to send responses to (e.g., "user_session:main")
    """
    user_message = messages[-1]["content"] if messages else ""
    message_lower = user_message.lower()

    # Discover all agents and their actions
    agents_info = self.discover_all_agents()

    # Build agent actions section for system prompt
    agent_actions_section = "\n## Agent Actions\n"
    agents_with_actions = [agent for agent in agents_info if agent.get('actions')]

    if agents_with_actions:
        agent_actions_section += "Some agents have special actions they can execute:\n\n"
        for agent in agents_with_actions:
            agent_name = agent['name']
            actions = agent.get('actions', [])
            agent_actions_section += f"**@{agent_name}** ({agent['role']}):\n"
            for action in actions:
                action_name = action.get('name', 'Unknown')
                action_desc = action.get('description', '')
                agent_actions_section += f"  - {action_name}: {action_desc}\n"
            agent_actions_section += "\n"

        agent_actions_section += "When users request these specific actions, delegate to the appropriate agent.\n"
        agent_actions_section += "Example: \"check my latest email\" → route to agent with email actions\n"
        agent_actions_section += "Example: \"get wikipedia summary for AI\" → route to agent with wikipedia actions\n"
    else:
        agent_actions_section += "No agents currently have special actions configured.\n"

    # Build dynamic agent delegation instructions based on available agents
    agent_examples = ""
    available_agent_names = [agent['name'] for agent in agents_info if agent['name'] != 'assistant']
    if available_agent_names:
        agent_examples = "\n## Agent Delegation\n"
        agent_examples += "To route tasks to other agents, start your response with the agent name preceded by the at-symbol.\n"
        agent_examples += f"Available agents: {', '.join(available_agent_names)}\n"
        agent_examples += "\nWARNING: NEVER use the at-symbol in explanatory text or examples - it triggers routing!\n"
        agent_examples += "Only use the at-symbol when you actually want to route a task to that agent.\n"
        agent_examples += "When explaining features to users, describe the agents WITHOUT using the at-symbol.\n"
    else:
        agent_examples = "\n## Agent Delegation\nNo other agents are currently available.\n"

    # Natural AI assistant system prompt
    system_prompt = f"""You are {self.name}, a helpful AI assistant that coordinates with specialized agents.

Be conversational and helpful. Keep responses brief and clear.
{agent_examples}
{agent_actions_section}

## How to Route Tasks

**For tasks requiring agent actions (email, wikipedia, etc.)**:
- Start your response with @agentname
- Example: User says "send a test email" → You respond "@bob please send a test email to test@example.com"
- Example: User says "check my emails" → You respond "@bob please check latest emails"
- DO NOT use functions for these - just route with @mention

**For agent lifecycle management only**:
- Use functions ONLY for: starting/stopping/creating/deleting agents
- Example: "start bob" → use smart_agent_operation function
- Example: "create an agent" → use create_agent function

## Available Functions (for agent lifecycle ONLY, not for task routing)
- get_agent_info() - Check agent status
- smart_agent_operation() - Start/stop/delete agents
- create_agent() - Create new agents (optionally with MCP tools)
- get_action_servers() - List available MCP action servers/tools
- assign_action_server() - Give an agent access to tools
- remove_action_server() - Remove tools from an agent

Keep responses natural and concise."""

    # AGENT MANAGEMENT FUNCTIONS: For creating, managing, and deleting agents
    agent_functions = [
        {
            "name": "manage_agents",
            "description": "Start, stop, or restart agents. Use for explicit agent management commands with EXACT agent names only.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["start", "stop", "restart"],
                        "description": "Action to perform on the agent"
                    },
                    "agent_name": {
                        "type": "string",
                        "description": "Name of the agent to manage"
                    }
                },
                "required": ["action", "agent_name"]
            }
        },
        {
            "name": "smart_agent_operation",
            "description": "Execute agent commands: start/stop/delete. Use when user commands action on specific agent.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["start", "stop", "delete"],
                        "description": "The action: start, stop, or delete"
                    },
                    "agent_name": {
                        "type": "string",
                        "description": "Name of the agent to act upon"
                    }
                },
                "required": ["action", "agent_name"]
            }
        },
        {
            "name": "get_agent_info",
            "description": "List all agents and their status. Use for status queries only, never for commands.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "get_runbook_examples",
            "description": "Show examples of existing agent runbooks and their structures. Use ONLY when user specifically asks to see existing agents or runbook patterns.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "create_agent",
            "description": "Create a new agent with specific capabilities. IMPORTANT: The role should be a short professional title (e.g., 'Data Analyst', 'Content Writer', 'Tax Expert') - NOT a long description. The backend automatically creates a proper runbook with job title. Optionally assign MCP action server for tool access.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name for the new agent (letters, numbers, underscores only, e.g., 'data_analyst', 'writer', 'translator')"
                    },
                    "role": {
                        "type": "string",
                        "description": "Short professional title (2-4 words max, e.g., 'Data Analyst', 'Content Writer', 'Tax Expert')"
                    },
                    "capabilities": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "Name of the capability (e.g., 'Data Analysis', 'Content Creation', 'Language Translation')"
                                },
                                "description": {
                                    "type": "string",
                                    "description": "Detailed description of what this capability does"
                                }
                            },
                            "required": ["name"]
                        },
                        "description": "List of capabilities for the new agent (at least one required)"
                    },
                    "action_server": {
                        "type": "string",
                        "description": "Optional: ID of MCP action server to give this agent tool access. Use 'email_mcp' for email tools. Only specify if user explicitly requests tool access (e.g., 'with email tools', 'give it email access')."
                    }
                },
                "required": ["name", "role", "capabilities"]
            }
        },
        {
            "name": "get_action_servers",
            "description": "Get list of available MCP action servers. ONLY use this when user explicitly asks 'what tools are available' or 'what servers exist'. Do NOT call this before assign_action_server.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "assign_action_server",
            "description": "Assign MCP tools to an existing agent. Use when user asks to 'give X email access', 'add email tools to X', etc. Known servers: email_mcp (for email tools). Just use email_mcp directly - no need to call get_action_servers first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "Name of the existing agent to assign tools to"
                    },
                    "action_server": {
                        "type": "string",
                        "description": "ID of the action server - use 'email_mcp' for email tools"
                    }
                },
                "required": ["agent_name", "action_server"]
            }
        },
        {
            "name": "remove_action_server",
            "description": "Remove MCP action server from an agent, removing its access to tools.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "Name of the agent to remove tools from"
                    }
                },
                "required": ["agent_name"]
            }
        },
        {
            "name": "delete_agent",
            "description": "Delete an existing agent. Use when users explicitly want to delete an agent.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the agent to delete (cannot be assistant, researcher, or synthesizer)"
                    },
                    "remove_runbook": {
                        "type": "boolean",
                        "description": "Whether to also remove the agent's runbook file (default: false, preserves runbook)",
                        "default": False
                    }
                },
                "required": ["name"]
            }
        }
    ]

    # Use the streaming completion method with function calling
    # Pass the full conversation history instead of just the latest message
    response_stream = self.get_streaming_completion(
        messages=messages,
        system_prompt=system_prompt,
        functions=agent_functions
    )

    if not response_stream:
        self.send_message(reply_to, "Sorry, I was unable to get a response.")
        return

    # Accumulate all chunks into a single response
    full_response = ""
    function_calls = []

    for chunk in response_stream:
        if chunk.startswith("FUNC:"):
            print(f"[DEBUG] Detected function call chunk: {chunk}", flush=True)
            # Extract function call information
            parts = chunk.split(":", 2)  # Split on first two colons
            if len(parts) >= 3:
                function_name = parts[1]
                function_args = parts[2]
                print(f"[DEBUG] Parsed function call: {function_name} with args: {function_args}", flush=True)
                function_calls.append((function_name, function_args))
            else:
                print(f"[DEBUG] Failed to parse function call, parts: {parts}", flush=True)
        else:
            full_response += chunk

    print(f"[DEBUG] Total function calls detected: {len(function_calls)}", flush=True)
    for i, (name, args) in enumerate(function_calls):
        print(f"[DEBUG] Function call {i+1}: {name} - {args}", flush=True)

    # PROCESS AGENT MANAGEMENT FUNCTION CALLS
    # Functions that should NOT send results to user (info-gathering only)
    silent_functions = ["get_agent_info", "get_runbook_examples"]

    if function_calls:
        function_results = []
        for function_name, function_args in function_calls:
            try:
                result = self._execute_agent_function(function_name, function_args, reply_to)

                # Only send to user if it's an action function (not info-gathering)
                if result and function_name not in silent_functions:
                    self.send_message(reply_to, result)

                # Store result for potential use in conversational response
                if result:
                    function_results.append((function_name, result))
            except Exception as e:
                error_msg = f"Error executing {function_name}: {str(e)}"
                print(f"[ASSISTANT] {error_msg}")
                self.send_message(reply_to, error_msg)

        # If there was a conversational response, send it
        # (The AI has incorporated function results into its response)
        if full_response.strip():
            self.send_message(reply_to, full_response)
        return

    # Send the regular response if there was one
    print(f"[ASSISTANT] Full response: '{full_response[:200]}...' (length: {len(full_response)})")
    if full_response.strip():
        print(f"[ASSISTANT] Full response is not empty, sending to user...")
        self.send_message(reply_to, full_response)

        # Check for direct agent mentions with task patterns (e.g., "AgentName, do something")
        if _contains_agent_task_pattern(self, full_response):
            print(f"[DEBUG] Detected agent task pattern, forwarding to agents...")
            _send_direct_agent_messages(self, full_response, reply_to)
        else:
            print(f"[DEBUG] No agent task pattern detected, skipping agent communication")
    else:
        print(f"[ASSISTANT] Full response is empty, skipping agent communication evaluation")


def _contains_agent_task_pattern(self, response: str) -> bool:
    """
    Check if response contains direct agent task patterns using simple regex.

    Pattern: "AgentName, [verb] ..." or "AgentName [verb] ..."

    This is much faster and more predictable than AI classification.

    Args:
        self: Reference to the AssistantAgent instance
        response: The response text to check for agent task patterns

    Returns:
        True if the response contains agent task patterns, False otherwise
    """
    import re

    if not response.strip():
        return False

    # Get available agents
    try:
        agents_info = self.discover_all_agents()
        agent_names = [agent['name'] for agent in agents_info] if agents_info else []
    except Exception as e:
        print(f"[ASSISTANT] Error discovering agents: {e}")
        return False

    if not agent_names:
        return False

    # Common task verbs
    task_verbs = r'(analyze|calculate|compute|translate|write|create|find|search|' \
                 r'research|summarize|explain|describe|list|show|tell|help|introduce|' \
                 r'generate|build|make|process|handle|check|verify|review)'

    # Check for patterns like "AgentName, verb..." or "AgentName verb..."
    for agent_name in agent_names:
        # Case-insensitive agent name matching with task verb
        pattern = rf'\b{re.escape(agent_name)}\b[,\s]+{task_verbs}'
        if re.search(pattern, response, re.IGNORECASE):
            print(f"[DEBUG] Found task pattern for agent: {agent_name}")
            return True

    return False


def _send_direct_agent_messages(self, response: str, reply_to: str):
    """
    Extract agent messages using regex pattern matching.

    Parses the response text for messages directed at specific agents and sends
    them natural language messages to execute tasks.

    Args:
        self: Reference to the AssistantAgent instance
        response: The response text containing agent mentions
        reply_to: Topic to route agent responses to
    """
    import re
    print(f"[DEBUG] _send_direct_agent_messages called with response: '{response[:100]}...'")

    # Get list of available agents
    try:
        agents_info = self.discover_all_agents()
        agent_names = [agent['name'] for agent in agents_info] if agents_info else []
        print(f"[DEBUG] Available agents: {agent_names}")
    except Exception as e:
        print(f"[DEBUG] Error discovering agents: {e}")
        return

    if not agent_names:
        print(f"[DEBUG] No agents available, skipping delegation")
        return

    # Extract messages for each agent using regex
    # Pattern: "AgentName, message" or "AgentName: message"
    for agent_name in agent_names:
        # Match "AgentName, message" or "AgentName: message" patterns
        pattern = rf'\b{re.escape(agent_name)}\b\s*[,:]\s*(.+?)(?:\n|$|\.(?:\s|$))'
        matches = re.finditer(pattern, response, re.IGNORECASE | re.MULTILINE)

        for match in matches:
            message = match.group(1).strip()
            if message and len(message) > 5:  # Filter out very short matches
                print(f"[ASSISTANT] Sending message to {agent_name}: '{message}'")
                _send_natural_message_to_agent(self, agent_name, message, reply_to)


def _sanitize_message_for_json(self, message: str) -> str:
    """
    Sanitize message content to ensure it can be safely serialized to JSON.

    Handles problematic characters and encoding issues that could prevent
    JSON serialization.

    Args:
        self: Reference to the AssistantAgent instance
        message: The message string to sanitize

    Returns:
        Sanitized message string safe for JSON serialization
    """
    if not message:
        return message

    try:
        # Test if the message can be JSON serialized
        import json
        json.dumps(message, ensure_ascii=False)
        return message  # Message is fine
    except (TypeError, ValueError, UnicodeEncodeError):
        # Message has problematic characters, sanitize it
        print(f"[DEBUG] Sanitizing message with problematic characters: '{message}'")

        # Replace or remove problematic characters
        sanitized = message

        # Handle common problematic character sequences
        replacements = {
            '...': '…',  # Replace multiple dots with ellipsis character
            '…': '…',   # Keep single ellipsis
            '"': '"',   # Replace smart quotes
            '"': '"',
            ''': "'",   # Replace smart apostrophes
            ''': "'",
            '–': '-',   # Replace en/em dashes
            '—': '-',
        }

        for old, new in replacements.items():
            sanitized = sanitized.replace(old, new)

        # Remove or replace other potentially problematic characters
        # But be conservative - only remove truly problematic ones
        problematic_chars = ['\u0000', '\u0001', '\u0002', '\u0003', '\u0004', '\u0005']
        for char in problematic_chars:
            sanitized = sanitized.replace(char, '')

        print(f"[DEBUG] Sanitized message: '{sanitized}'")
        return sanitized


def _send_natural_message_to_agent(self, agent_name: str, message: str, reply_to: str):
    """
    Send a natural conversation message to a specific agent, including conversation history.

    This method maintains conversation history with each agent and sends the full
    context when communicating, allowing agents to maintain conversational context.

    Args:
        self: Reference to the AssistantAgent instance
        agent_name: Name of the agent to send the message to
        message: The message content to send
        reply_to: Topic where the agent should route its response
    """
    try:
        # Get or create conversation history for this agent
        if agent_name not in self.agent_conversations:
            self.agent_conversations[agent_name] = []

        # Sanitize the message first to handle special characters
        sanitized_message = _sanitize_message_for_json(self, message)

        # Add the sanitized message from the assistant to the history
        self.agent_conversations[agent_name].append({"role": "user", "content": sanitized_message})

        # Create message data with full history for the worker agent
        # The worker will see the assistant as the 'user' in this context
        message_data = {
            "messages": self.agent_conversations[agent_name],
        }

        # Validate message data before sending (additional check for any remaining issues)
        try:
            import json
            # Test JSON serialization to catch any remaining character encoding issues
            json_test = json.dumps(message_data, ensure_ascii=False)
            print(f"[DEBUG] JSON serialization successful for message to {agent_name}")
        except (TypeError, ValueError, UnicodeEncodeError) as e:
            print(f"[ASSISTANT] JSON serialization error for message to {agent_name}: {e}")
            print(f"[DEBUG] Problematic message data: {message_data}")
            # Remove the problematic message from history to prevent future issues
            if self.agent_conversations[agent_name]:
                self.agent_conversations[agent_name].pop()
            return False

        # Use the base agent communication method
        success = self.communicate_with_agent(
            agent_name,
            message_data,
            "assistant_coordination",
            original_user_topic=reply_to  # Pass the user's reply topic
        )
        if success:
            print(f"[ASSISTANT] Sent natural message with history to {agent_name}")
        else:
            print(f"[ASSISTANT] Failed to send message to {agent_name}")
    except Exception as e:
        print(f"[ASSISTANT] Error sending natural message to {agent_name}: {e}")
