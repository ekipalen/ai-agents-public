# agentkit/agentkit/base.py
import os
import time
import uuid
import json
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from .messaging import RedisMessenger
from .ai import AIClient
from .discovery import AgentDiscovery, AgentRunbook, AgentCapability
from .constants import TOPIC_AGENT_INBOX


class BaseAgent:
    """Base class for all agents with messaging, AI, and discovery capabilities."""

    def __init__(
        self,
        name: str,
        role: Optional[str] = None,
        inbox_topic: Optional[str] = None,
        runbook: Optional[AgentRunbook] = None
    ):
        # Load environment variables
        project_root = Path(__file__).parent.parent.parent
        load_dotenv(dotenv_path=project_root / ".env")

        # Basic attributes
        self.id = str(uuid.uuid4())
        self.name = name
        self.role = role
        self.runbook = runbook
        self.startup_time = time.time()
        self.orchestrator_url = os.getenv("ORCHESTRATOR_URL", "http://localhost:9000")
        self.status_endpoint = f"/agent/{self.id}/status"
        self.collaboration_history: List[Dict[str, Any]] = []

        # Setup inbox topic
        self.inbox_topic = inbox_topic if inbox_topic else TOPIC_AGENT_INBOX.format(name)

        # Initialize messaging
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        self.messenger = RedisMessenger(redis_host, redis_port, self.name)

        # Initialize AI client
        openai_api_key = os.getenv("OPENAI_API_KEY")
        self.ai = AIClient(openai_api_key, self.name) if openai_api_key else None

        # Initialize discovery
        self.discovery = AgentDiscovery(self.orchestrator_url, self.name)

        # Actions support
        self.actions: List[Dict[str, Any]] = []
        self.action_server_name: Optional[str] = None

        # Legacy attributes for backward compatibility
        self.redis_client = None
        self.openai_client = None
        self.available_agents = {}

    def _connect_redis(self):
        """Connect to Redis server (delegates to messenger)."""
        success = self.messenger.connect()
        if success:
            self.redis_client = self.messenger.redis_client  # Backward compatibility
        return success

    def get_completion(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None
    ) -> Optional[str]:
        """Get completion from OpenAI (delegates to AI client)."""
        if not self.ai:
            print(f"[{self.name}] Cannot get completion, AI client not initialized.", flush=True)
            return None
        return self.ai.get_completion(messages, system_prompt)

    def get_streaming_completion(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        functions: Optional[List[Dict]] = None
    ):
        """Get streaming completion from OpenAI (delegates to AI client)."""
        if not self.ai:
            print(f"[{self.name}] Cannot get streaming completion, AI client not initialized.", flush=True)
            return
        return self.ai.get_streaming_completion(messages, system_prompt, functions)


    def register(self):
        """Registers the agent with the orchestrator."""
        registration_data = {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "inbox_topic": self.inbox_topic,
            "status_endpoint": self.status_endpoint,
        }
        try:
            response = requests.post(
                f"{self.orchestrator_url}/agents/register",
                json=registration_data,
            )
            response.raise_for_status()
            print(f"Agent {self.name} ({self.id}) registered successfully.", flush=True)
            return response.json()
        except requests.RequestException as e:
            print(f"Failed to register agent {self.name}: {e}", flush=True)
            return None

    def send_message(self, topic: str, message) -> bool:
        """Send message to Redis topic (delegates to messenger)."""
        return self.messenger.send_message(topic, message)
    
    def _message_handler(self, message: dict):
        """Handles incoming messages. Should be overridden by subclasses."""
        import json

        raw_data = message['data'].decode()
        print(f"Received message on topic {message['channel']}: {raw_data[:100]}...", flush=True)

        # Try to parse as JSON, fall back to raw string
        try:
            parsed_data = json.loads(raw_data)
            print(f"[DEBUG] Parsed JSON message: {type(parsed_data)}", flush=True)
        except json.JSONDecodeError:
            parsed_data = raw_data
            print(f"[DEBUG] Message is plain text: {type(parsed_data)}", flush=True)

        # Store parsed data for subclasses to use
        message['parsed_data'] = parsed_data

    def subscribe(self, topic: str):
        """Subscribe to topic in background thread (delegates to messenger)."""
        self.messenger.subscribe(topic, self._message_handler)

    def _discover_and_start_agents(self, reply_to: str = None) -> List[Dict]:
        """Discover all agents, check their status, and start needed ones."""
        try:
            # Use the assistant's discover_all_agents method if available
            if hasattr(self, 'discover_all_agents'):
                all_agents_info = self.discover_all_agents()
            else:
                # Fallback to basic discovery
                response = requests.get(f"{self.orchestrator_url}/agents/runbooks")
                if response.status_code != 200:
                    return []

                runbooks_data = response.json()
                # Get running status
                running_response = requests.get(f"{self.orchestrator_url}/agents")
                running_agents = []
                if running_response.status_code == 200:
                    running_data = running_response.json()
                    running_agents = [agent['name'] for agent in running_data if agent.get('status') == 'running']

                all_agents_info = []
                for runbook in runbooks_data:
                    agent_name = runbook.get('agent_name', '')
                    if agent_name == self.name:  # Skip self
                        continue

                    all_agents_info.append({
                        'name': agent_name,
                        'role': runbook.get('role', 'Unknown role'),
                        'capabilities': [cap.get('name', 'Unknown') for cap in runbook.get('capabilities', [])],
                        'is_running': agent_name in running_agents,
                        'status': 'running' if agent_name in running_agents else 'stopped'
                    })

            if not all_agents_info:
                return []

            # Check which agents need to be started
            agents_to_start = []
            for agent_info in all_agents_info:
                if not agent_info.get('is_running', False):
                    agents_to_start.append(agent_info['name'])

            # Start needed agents
            if agents_to_start and hasattr(self, 'start_agent'):
                if reply_to:
                    self.send_message(reply_to, f"🚀 Starting {len(agents_to_start)} agent(s) needed for this task: {', '.join(agents_to_start)}")

                for agent_name in agents_to_start:
                    if reply_to:
                        self.send_message(reply_to, f"⚙️ Starting {agent_name}...")
                    success = self.start_agent(agent_name)
                    if success:
                        if reply_to:
                            self.send_message(reply_to, f"✅ {agent_name} started successfully")
                        # Update the agent info to reflect new status
                        for agent in all_agents_info:
                            if agent['name'] == agent_name:
                                agent['is_running'] = True
                                agent['status'] = 'running'
                    else:
                        if reply_to:
                            self.send_message(reply_to, f"❌ Failed to start {agent_name}")

                # Agents should be ready immediately
                pass

            return all_agents_info

        except Exception as e:
            print(f"Error in _discover_and_start_agents: {e}", flush=True)
            return []

    def discover_agents(self) -> Dict[str, AgentRunbook]:
        """Discover available agents (delegates to discovery)."""
        self.available_agents = self.discovery.discover_agents()
        return self.available_agents

    def _get_agent_capability_name(self, agent_name: str) -> str:
        """Get the first capability name from an agent's runbook."""
        if not self.available_agents or agent_name not in self.available_agents:
            return "general"

        agent_runbook = self.available_agents[agent_name]
        if hasattr(agent_runbook, 'capabilities') and agent_runbook.capabilities:
            # Return the first capability name, cleaned for agent_type matching
            capability_name = agent_runbook.capabilities[0].name
            return capability_name.replace(" ", "_").lower()
        return "general"

    def find_agent_for_task(self, task_description: str, tags: Optional[List[str]] = None) -> Optional[str]:
        """Find best agent for task (delegates to discovery)."""
        return self.discovery.find_agent_for_task(task_description, tags)

    def decompose_task(self, complex_task: str) -> List[Dict[str, Any]]:
        """Use OpenAI to decompose a complex task into smaller subtasks."""
        if not self.ai:
            return [{"task": complex_task, "agent": None, "reasoning": "No OpenAI client available"}]

        prompt = f"""
        Break down this complex task into 3-5 smaller, manageable subtasks that different agents can handle:

        Task: {complex_task}

        Create concise subtasks that can be completed quickly. Consider:
        - Research/Planning agents for gathering information
        - Creative agents for content generation
        - Review agents for quality assurance

        Return a JSON array (3-5 items max) where each object has:
        - "task": the specific subtask (keep under 100 characters)
        - "agent_type": suggested agent specialization (1-2 words)
        - "priority": 1-5 (5 being highest)
        - "dependencies": array of other subtask indices this depends on

        Focus on efficiency - fewer, more focused tasks work better.
        """

        try:
            result = self.get_completion(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are a task decomposition specialist. Break down complex tasks into actionable subtasks."
            )
            if result:
                # Try to parse JSON response
                try:
                    return json.loads(result)
                except json.JSONDecodeError:
                    # Smart fallback based on task complexity (not just length)
                    task_lower = complex_task.lower()
                    task_length = len(complex_task.split())

                    # Keywords that indicate complex research topics
                    complex_keywords = ['research', 'analyze', 'strategy', 'future', 'development', 'comprehensive', 'explore', 'investigate']
                    has_complex_keywords = any(keyword in task_lower for keyword in complex_keywords)

                    # Use multiple agents for complex topics or longer tasks
                    if task_length < 8 and not has_complex_keywords:
                        # Simple short tasks - single agent
                        return [{"task": complex_task, "agent_type": "general", "priority": 5, "dependencies": []}]
                    elif task_length < 15 or has_complex_keywords:
                        # Medium complexity - 2 agents
                        if not self.available_agents:
                            self.discover_agents()
                        available_agents = list(self.available_agents.keys()) if self.available_agents else []

                        if len(available_agents) >= 2:
                            agent1_cap = self._get_agent_capability_name(available_agents[0])
                            agent2_cap = self._get_agent_capability_name(available_agents[1])
                        else:
                            agent1_cap = "research"
                            agent2_cap = "creative"

                        return [
                            {"task": f"Research and gather information about: {complex_task[:50]}...", "agent_type": agent1_cap, "priority": 5, "dependencies": []},
                            {"task": f"Create comprehensive response for: {complex_task[:50]}...", "agent_type": agent2_cap, "priority": 4, "dependencies": [0]}
                        ]
                    else:
                        # High complexity - 3 agents
                        if not self.available_agents:
                            self.discover_agents()
                        available_agents = list(self.available_agents.keys()) if self.available_agents else []

                        if len(available_agents) >= 3:
                            agent1_cap = self._get_agent_capability_name(available_agents[0])
                            agent2_cap = self._get_agent_capability_name(available_agents[1])
                            agent3_cap = self._get_agent_capability_name(available_agents[2])
                        elif len(available_agents) >= 2:
                            agent1_cap = self._get_agent_capability_name(available_agents[0])
                            agent2_cap = self._get_agent_capability_name(available_agents[1])
                            agent3_cap = agent2_cap  # Use second agent for review task too
                        else:
                            agent1_cap = "research"
                            agent2_cap = "creative"
                            agent3_cap = "review"

                        return [
                            {"task": f"Research and gather information about: {complex_task[:50]}...", "agent_type": agent1_cap, "priority": 5, "dependencies": []},
                            {"task": f"Create content based on: {complex_task[:50]}...", "agent_type": agent2_cap, "priority": 4, "dependencies": [0]},
                            {"task": f"Review and improve the content for: {complex_task[:50]}...", "agent_type": agent3_cap, "priority": 3, "dependencies": [1]}
                        ]
            else:
                # Fallback: create appropriate number of subtasks based on task complexity
                task_length = len(complex_task.split())

                if task_length < 10:
                    # Simple task - just one comprehensive task
                    return [
                        {"task": f"Handle this request: {complex_task}", "agent_type": "general", "priority": 5, "dependencies": []}
                    ]
                elif task_length < 20:
                    # Medium complexity - two tasks
                    if not self.available_agents:
                        self.discover_agents()
                    available_agents = list(self.available_agents.keys()) if self.available_agents else []

                    if len(available_agents) >= 2:
                        agent1_cap = self._get_agent_capability_name(available_agents[0])
                        agent2_cap = self._get_agent_capability_name(available_agents[1])
                    else:
                        agent1_cap = "research"
                        agent2_cap = "creative"

                    return [
                        {"task": f"Research and gather information about: {complex_task[:50]}...", "agent_type": agent1_cap, "priority": 5, "dependencies": []},
                        {"task": f"Create comprehensive response for: {complex_task[:50]}...", "agent_type": agent2_cap, "priority": 4, "dependencies": [0]}
                    ]
                else:
                    # Complex task - three tasks
                    if not self.available_agents:
                        self.discover_agents()
                    available_agents = list(self.available_agents.keys()) if self.available_agents else []

                    if len(available_agents) >= 3:
                        agent1_cap = self._get_agent_capability_name(available_agents[0])
                        agent2_cap = self._get_agent_capability_name(available_agents[1])
                        agent3_cap = self._get_agent_capability_name(available_agents[2])
                    elif len(available_agents) >= 2:
                        agent1_cap = self._get_agent_capability_name(available_agents[0])
                        agent2_cap = self._get_agent_capability_name(available_agents[1])
                        agent3_cap = agent2_cap  # Use second agent for review task too
                    else:
                        agent1_cap = "research"
                        agent2_cap = "creative"
                        agent3_cap = "review"

                    return [
                        {"task": f"Research and gather information about: {complex_task[:50]}...", "agent_type": agent1_cap, "priority": 5, "dependencies": []},
                        {"task": f"Create content based on: {complex_task[:50]}...", "agent_type": agent2_cap, "priority": 4, "dependencies": [0]},
                        {"task": f"Review and improve the content for: {complex_task[:50]}...", "agent_type": agent3_cap, "priority": 3, "dependencies": [1]}
                    ]
        except Exception as e:
            print(f"Error decomposing task: {e}", flush=True)
            # Smart fallback based on task length and available agents
            task_length = len(complex_task.split())

            if task_length < 10:
                return [{"task": complex_task, "agent_type": "general", "priority": 5, "dependencies": []}]
            else:
                # Use available agents' capabilities for fallback
                if not self.available_agents:
                    self.discover_agents()
                available_agents = list(self.available_agents.keys()) if self.available_agents else []

                if len(available_agents) >= 2:
                    agent1_cap = self._get_agent_capability_name(available_agents[0])
                    agent2_cap = self._get_agent_capability_name(available_agents[1])
                    agent3_cap = agent2_cap  # Use second agent for review task too
                else:
                    agent1_cap = "research"
                    agent2_cap = "creative"
                    agent3_cap = "review"

                return [
                    {"task": f"Research and gather information about: {complex_task[:50]}...", "agent_type": agent1_cap, "priority": 5, "dependencies": []},
                    {"task": f"Create content based on: {complex_task[:50]}...", "agent_type": agent2_cap, "priority": 4, "dependencies": [0]},
                    {"task": f"Review and improve the content for: {complex_task[:50]}...", "agent_type": agent3_cap, "priority": 3, "dependencies": [1]}
                ]

    def delegate_task(self, agent_name: str, task_data: Dict[str, Any], reply_to: str = None) -> bool:
        """Delegate a task to another agent."""
        if agent_name not in self.available_agents:
            print(f"Agent {agent_name} not available for delegation", flush=True)
            return False

        target_topic = f"agent:{agent_name}:inbox"

        delegation_message = {
            "from_agent": self.name,
            "task": task_data,
            "reply_to": self.inbox_topic,  # Always send responses to delegating agent's inbox
            "user_topic": reply_to,  # Keep track of user topic for final responses
            "timestamp": time.time()
        }

        # Record the delegation in collaboration history
        self.collaboration_history.append({
            "type": "delegation",
            "to_agent": agent_name,
            "task": task_data,
            "timestamp": time.time()
        })

        self.send_message(target_topic, json.dumps(delegation_message))

        return True

    # ===== NATURAL AGENT COMMUNICATION =====

    def communicate_with_agent(self, target_agent_name: str, message: any, context: str = None, original_user_topic: str = None) -> bool:
        """
        Send a natural, conversational message to another agent.
        This allows agents to communicate organically without rigid protocols.

        Args:
            target_agent_name: Name of the agent to communicate with
            message: The natural language message or data dict to send
            context: Optional context about why you're communicating
            original_user_topic: The original topic for user-facing responses

        Returns:
            True if message sent successfully
        """
        # Check if target agent is available
        if not self._is_agent_running(target_agent_name):
            print(f"[{self.name}] Cannot communicate with {target_agent_name} - agent not running")
            return False

        # Create a natural conversation message
        if isinstance(message, dict):
            conversation_data = message
        else:
            conversation_data = {"message": str(message)}

        conversation_data.update({
            "collaboration_type": "natural_conversation",
            "from_agent": self.name,
            "context": context or "",
            "timestamp": time.time(),
            "reply_to": self.inbox_topic,
            "original_user_topic": original_user_topic
        })

        target_topic = f"agent:{target_agent_name}:inbox"
        success = self.send_message(target_topic, json.dumps(conversation_data))

        if success:
            message_preview = str(message)[:50] if not isinstance(message, dict) else json.dumps(message)[:50]
            print(f"[{self.name}] Sent natural message to {target_agent_name}: {message_preview}...")
        else:
            print(f"[{self.name}] Failed to send message to {target_agent_name}")

        return success

    # ===== HELPER METHODS =====

    def _is_agent_running(self, agent_name: str) -> bool:
        """Check if agent is running (delegates to discovery)."""
        return self.discovery.is_agent_running(agent_name)

    def _get_agent_capabilities(self, agent_name: str) -> List[str]:
        """Get agent capabilities (delegates to discovery)."""
        return self.discovery.get_agent_capabilities(agent_name)

    def collaborate_on_task(self, complex_task: str, reply_to: str = None) -> bool:
        """Main method to collaborate on a complex task by decomposing it and delegating subtasks."""


        # Send initial collaboration status
        if reply_to:
            # Add a brief pause before announcing analysis to make it feel more thoughtful
            import time
            time.sleep(0.8)

            self.send_message(reply_to, "🤖 Analyzing your request...")

            # Add a brief pause to make it feel more realistic
            time.sleep(1.0)

            # Discover all agents (running or not) and start needed ones
            all_agents_info = self._discover_and_start_agents(reply_to)
            if not all_agents_info:
                self.send_message(reply_to, "❌ No agents available for collaboration.")
                return False

            # Update available_agents with the agents we just ensured are running
            self.available_agents = {}
            for agent_info in all_agents_info:
                if agent_info.get('is_running', False):
                    # Create runbook from agent info
                    runbook = AgentRunbook(
                        agent_name=agent_info["name"],
                        role=agent_info["role"],
                        capabilities=[
                            AgentCapability(name=cap, description="", parameters={}, example_usage="", tags=[])
                            for cap in agent_info.get('capabilities', [])
                        ],
                        collaboration_patterns=[],
                        dependencies=[]
                    )
                    self.available_agents[agent_info["name"]] = runbook

            # Decompose the task
            subtasks = self.decompose_task(complex_task)

            # Send combined status update
            agent_list = ', '.join(self.available_agents.keys())
            self.send_message(reply_to, f"🚀 **Collaboration Started** - Found {len(self.available_agents)} agents ({agent_list}) and broke down into {len(subtasks)} tasks")

        # Delegate each subtask to appropriate agents
        if reply_to and subtasks:
            # Create a comprehensive delegation message with all assignments
            delegation_msg = f"🔄 **Delegating {len(subtasks)} Tasks to Agents:**\n"

            # Collect all assignments first
            assignments = []
            for i, subtask in enumerate(subtasks):
                agent_name = self.find_agent_for_task(
                    subtask.get("task", ""),
                    subtask.get("agent_type", "").split()
                )

                if agent_name:
                    agent_type = subtask.get("agent_type", "general")
                    task_preview = subtask["task"][:50] + "..." if len(subtask["task"]) > 50 else subtask["task"]

                    assignments.append(f"**{agent_name}** ({agent_type}) • {task_preview}")

                    task_data = {
                        "task": subtask["task"],
                        "priority": subtask.get("priority", 3),
                        "dependencies": subtask.get("dependencies", []),
                        "subtask_index": i,
                        "total_subtasks": len(subtasks),
                        "original_query": complex_task
                    }

                    self.delegate_task(agent_name, task_data, reply_to)

                    # No delay needed between delegations
                    pass
                else:
                    assignments.append(f"⚠️ No agent found • {subtask['task'][:50]}...")

            # Add all assignments to the message
            delegation_msg += "\n".join(assignments)

            # Send the complete delegation message
            self.send_message(reply_to, delegation_msg)

            self.send_message(reply_to, f"📤 All {len(subtasks)} tasks delegated! Agents are now working...")

        return True

    def register_runbook(self) -> bool:
        """Register agent's runbook (delegates to discovery)."""
        if not self.runbook:
            print(f"[{self.name}] No runbook defined", flush=True)
            return False
        return self.discovery.register_runbook(self.runbook)

    # ===== ACTION MANAGEMENT =====

    def load_actions(self) -> bool:
        """
        Load actions from the orchestrator.
        Should be called after agent registration.

        Returns:
            True if actions loaded successfully
        """
        try:
            response = requests.get(
                f"{self.orchestrator_url}/agents/{self.name}/actions",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                self.actions = data.get("actions", [])
                action_server_info = data.get("action_server")
                if action_server_info:
                    self.action_server_name = action_server_info.get("name")
                print(f"[{self.name}] Loaded {len(self.actions)} action(s)", flush=True)
                return True
            else:
                print(f"[{self.name}] Failed to load actions: {response.status_code}", flush=True)
                return False
        except requests.RequestException as e:
            print(f"[{self.name}] Error loading actions: {e}", flush=True)
            return False

    def execute_action(self, action_id: str, parameters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute an action via the orchestrator.

        Args:
            action_id: ID of the action to execute
            parameters: Parameters for the action

        Returns:
            Result dictionary with 'result' and 'error' keys, or None if failed
        """
        try:
            response = requests.post(
                f"{self.orchestrator_url}/agents/{self.name}/actions/execute",
                json={"action_id": action_id, "parameters": parameters},
                timeout=30
            )
            if response.status_code == 200:
                return response.json()
            else:
                print(f"[{self.name}] Failed to execute action: {response.status_code}", flush=True)
                return {"result": None, "error": f"HTTP {response.status_code}"}
        except requests.RequestException as e:
            print(f"[{self.name}] Error executing action: {e}", flush=True)
            return {"result": None, "error": str(e)}

    def list_actions(self) -> List[Dict[str, Any]]:
        """
        List all available actions for this agent.

        Returns:
            List of action dictionaries
        """
        return self.actions

    def has_action(self, action_id: str) -> bool:
        """
        Check if agent has a specific action.

        Args:
            action_id: ID of the action

        Returns:
            True if action exists and is enabled
        """
        for action in self.actions:
            if action.get("id") == action_id and action.get("enabled", True):
                return True
        return False

    def get_action(self, action_id: str) -> Optional[Dict[str, Any]]:
        """
        Get action details by ID.

        Args:
            action_id: ID of the action

        Returns:
            Action dictionary or None if not found
        """
        for action in self.actions:
            if action.get("id") == action_id:
                return action
        return None

    def run(self):
        """Starts the agent's main loop with enhanced collaboration capabilities."""
        print(f"Agent {self.name} is running with collaboration capabilities.", flush=True)

        try:
            self._connect_redis()
            print(f"[{self.name}] Redis connection established", flush=True)
        except Exception as e:
            print(f"[{self.name}] ❌ Failed to connect to Redis: {e}", flush=True)
            return

        try:
            self.register()
            print(f"[{self.name}] Registered with orchestrator", flush=True)
        except Exception as e:
            print(f"[{self.name}] ⚠️ Failed to register: {e}", flush=True)

        # Register runbook if available
        if self.runbook:
            try:
                self.register_runbook()
                print(f"[{self.name}] Runbook registered", flush=True)
            except Exception as e:
                print(f"[{self.name}] ⚠️ Failed to register runbook: {e}", flush=True)

        # Load actions if available
        try:
            self.load_actions()
            if self.actions:
                print(f"[{self.name}] 🔧 Actions loaded: {[a.get('name') for a in self.actions]}", flush=True)
        except Exception as e:
            print(f"[{self.name}] ⚠️ Failed to load actions: {e}", flush=True)

        try:
            print(f"[{self.name}] Attempting to subscribe to {self.inbox_topic}...", flush=True)
            self.subscribe(self.inbox_topic)
            print(f"[{self.name}] ✅ Subscription initiated", flush=True)
        except Exception as e:
            print(f"[{self.name}] ❌ Failed to subscribe: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return

        # In the future, this is where the main logic and message handling will go.
        try:
            print(f"[{self.name}] Entering main loop...", flush=True)
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"Agent {self.name} shutting down.", flush=True)
