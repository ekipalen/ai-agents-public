"""Agent discovery and capability matching."""
import requests
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class AgentCapability:
    """Defines a specific capability an agent can perform."""
    name: str
    description: str
    parameters: Dict
    example_usage: str
    tags: List[str]


@dataclass
class AgentRunbook:
    """Complete runbook for an agent including capabilities."""
    agent_name: str
    role: str
    capabilities: List[AgentCapability]
    collaboration_patterns: List[str]
    dependencies: List[str]
    version: str = "1.0.0"
    job_title: str = "AI Agent"

    def to_dict(self) -> Dict:
        """Convert runbook to dictionary format."""
        return {
            "agent_name": self.agent_name,
            "role": self.role,
            "job_title": self.job_title,
            "capabilities": [
                {
                    "name": cap.name,
                    "description": cap.description,
                    "parameters": cap.parameters,
                    "example_usage": cap.example_usage,
                    "tags": cap.tags
                }
                for cap in self.capabilities
            ],
            "collaboration_patterns": self.collaboration_patterns,
            "dependencies": self.dependencies,
            "version": self.version
        }


class AgentDiscovery:
    """Handles agent discovery and capability lookups."""

    def __init__(self, orchestrator_url: str, agent_name: str):
        self.orchestrator_url = orchestrator_url
        self.agent_name = agent_name
        self.available_agents: Dict[str, AgentRunbook] = {}

    def discover_agents(self) -> Dict[str, AgentRunbook]:
        """
        Discover available agents and their capabilities from orchestrator.

        Returns:
            Dict mapping agent names to their runbooks
        """
        try:
            response = requests.get(f"{self.orchestrator_url}/agents/runbooks")
            if response.status_code != 200:
                print(f"[{self.agent_name}] Failed to fetch runbooks: {response.status_code}", flush=True)
                return {}

            runbooks_data = response.json()
            self.available_agents = {}

            for agent_data in runbooks_data:
                # Skip self to avoid self-delegation
                if agent_data["agent_name"] == self.agent_name:
                    continue

                runbook = AgentRunbook(
                    agent_name=agent_data["agent_name"],
                    role=agent_data["role"],
                    capabilities=[
                        AgentCapability(**cap) for cap in agent_data["capabilities"]
                    ],
                    collaboration_patterns=agent_data["collaboration_patterns"],
                    dependencies=agent_data["dependencies"],
                    version=agent_data.get("version", "1.0.0"),
                    job_title=agent_data.get("job_title", "AI Agent")
                )
                self.available_agents[agent_data["agent_name"]] = runbook

            print(f"[{self.agent_name}] Discovered {len(self.available_agents)} agents", flush=True)
            return self.available_agents

        except Exception as e:
            print(f"[{self.agent_name}] Error discovering agents: {e}", flush=True)
            return {}

    def is_agent_running(self, agent_name: str) -> bool:
        """
        Check if an agent is currently running.

        Args:
            agent_name: Name of agent to check

        Returns:
            True if agent is running, False otherwise
        """
        try:
            response = requests.get(f"{self.orchestrator_url}/agents")
            if response.status_code == 200:
                agents = response.json()
                for agent in agents:
                    if agent.get('name') == agent_name:
                        return agent.get('status') == 'running'
        except Exception as e:
            print(f"[{self.agent_name}] Error checking agent status: {e}", flush=True)
        return False

    def get_agent_capabilities(self, agent_name: str) -> List[str]:
        """
        Get capabilities of a specific agent.

        Args:
            agent_name: Name of agent

        Returns:
            List of capability names
        """
        if agent_name in self.available_agents:
            runbook = self.available_agents[agent_name]
            return [cap.name for cap in runbook.capabilities]
        return []

    def find_agent_for_task(self, task_description: str, tags: Optional[List[str]] = None) -> Optional[str]:
        """
        Find the best agent for a specific task (simple round-robin for now).

        Args:
            task_description: Description of the task
            tags: Optional tags for filtering

        Returns:
            Agent name or None if no agents available
        """
        if not self.available_agents:
            self.discover_agents()

        if not self.available_agents:
            return None

        # Simple round-robin assignment
        if not hasattr(self, '_last_assigned_agent_index'):
            self._last_assigned_agent_index = 0

        available_agent_names = list(self.available_agents.keys())
        agent_name = available_agent_names[self._last_assigned_agent_index]

        self._last_assigned_agent_index = (
            (self._last_assigned_agent_index + 1) % len(available_agent_names)
        )

        return agent_name

    def register_runbook(self, runbook: AgentRunbook) -> bool:
        """
        Register agent's runbook with orchestrator.

        Args:
            runbook: AgentRunbook to register

        Returns:
            True if successful, False otherwise
        """
        try:
            response = requests.post(
                f"{self.orchestrator_url}/agents/runbooks",
                json=runbook.to_dict()
            )
            if response.status_code == 200:
                print(f"[{self.agent_name}] Runbook registered successfully", flush=True)
                return True
            else:
                print(f"[{self.agent_name}] Failed to register runbook: {response.status_code}", flush=True)
                return False
        except Exception as e:
            print(f"[{self.agent_name}] Error registering runbook: {e}", flush=True)
            return False
