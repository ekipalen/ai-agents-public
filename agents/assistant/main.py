print("--- [ASSISTANT] main.py TOP ---", flush=True)

import sys
import os

# Add the project root to the path so we can import agentkit
# __file__ is agents/assistant/main.py, so we need to go up 2 levels to get to project root
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'agentkit'))

from agentkit import BaseAgent
from agentkit.runbook_loader import RunbookLoader
import json
import time

# Import the refactored modules (regular imports, not relative)
import agent_operations
import ai_functions
import collaboration
import message_handling

print("--- [ASSISTANT] Imports complete ---", flush=True)

class AssistantAgent(BaseAgent):
    def __init__(self):
        try:
            # Load runbook from external markdown file
            runbooks_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'runbooks')
            loader = RunbookLoader(runbooks_dir)
            runbook = loader.load_runbook("assistant")

            print(f"[ASSISTANT] Successfully loaded runbook with {len(runbook.capabilities)} capabilities")
            print(f"[ASSISTANT] Role: {runbook.role[:100]}...")

        except Exception as e:
            print(f"[ASSISTANT] Failed to load runbook: {e}")
            print("[ASSISTANT] Falling back to basic configuration...")

            # Fallback runbook if loading fails
            from agentkit import AgentRunbook, AgentCapability
            runbook = AgentRunbook(
                agent_name="assistant",
                role="Intelligent task orchestrator and general-purpose assistant.",
                capabilities=[
                    AgentCapability(
                        name="general_assistance",
                        description="Provide helpful responses to general questions and requests",
                        parameters={"query": "The user's question or request"},
                        example_usage="Answer questions about various topics",
                        tags=["general", "information", "help"]
                    )
                ],
                collaboration_patterns=["Basic assistance capabilities"],
                dependencies=[]
            )

        super().__init__(
            name="assistant",
            role=runbook.role,
            runbook=runbook
        )
        self.agent_conversations = {}

    # ============================================================================
    # MESSAGE HANDLING - Delegated to message_handling module
    # ============================================================================

    def _message_handler(self, message: dict):
        """Handles an incoming user prompt with intelligent task routing and collaboration."""
        return message_handling._message_handler(self, message)

    def _enhance_messages_with_agent_history(self, messages):
        """Enhance the message list with relevant agent conversation history."""
        return message_handling._enhance_messages_with_agent_history(self, messages)

    def _handle_direct_response(self, messages, reply_to):
        """Handle simple tasks with direct AI response using runbook capabilities."""
        return message_handling._handle_direct_response(self, messages, reply_to)

    def _contains_agent_task_pattern(self, response: str) -> bool:
        """Check if response contains direct agent task patterns using simple regex."""
        return message_handling._contains_agent_task_pattern(self, response)

    def _send_direct_agent_messages(self, response: str, reply_to: str):
        """Extract agent messages using regex pattern matching."""
        return message_handling._send_direct_agent_messages(self, response, reply_to)

    def _sanitize_message_for_json(self, message: str) -> str:
        """Sanitize message content to ensure it can be safely serialized to JSON."""
        return message_handling._sanitize_message_for_json(self, message)

    def _send_natural_message_to_agent(self, agent_name: str, message: str, reply_to: str):
        """Send a natural conversation message to a specific agent, including conversation history."""
        return message_handling._send_natural_message_to_agent(self, agent_name, message, reply_to)

    # ============================================================================
    # AGENT OPERATIONS - Delegated to agent_operations module
    # ============================================================================

    def discover_all_agents(self):
        """Query the orchestrator for ALL agents (running or not) and their capabilities."""
        return agent_operations.discover_all_agents(self)

    def _clear_agents_cache(self):
        """Clear the cached agent data to force fresh fetch on next request."""
        return agent_operations._clear_agents_cache(self)

    def start_agent(self, agent_name: str) -> bool:
        """Start an agent if it's not already running."""
        return agent_operations.start_agent(self, agent_name)

    def stop_agent(self, agent_name: str) -> bool:
        """Stop an agent if it's currently running."""
        return agent_operations.stop_agent(self, agent_name)

    def _handle_agent_management_command(self, command_string: str, reply_to: str):
        """Handle direct agent management commands like start/stop all agents."""
        return agent_operations._handle_agent_management_command(self, command_string, reply_to)

    def manage_agents(self, action: str, target: str = "all", reply_to: str = None):
        """Manage agents - can be called by AI when users request agent management."""
        return agent_operations.manage_agents(self, action, target, reply_to)

    def smart_agent_operation(self, action: str, agent_name: str, reply_to: str = None):
        """Smart agent operations using AI reasoning to resolve agent names."""
        return agent_operations.smart_agent_operation(self, action, agent_name, reply_to)

    def get_agent_info(self, reply_to: str = None):
        """Get comprehensive agent information for AI decision making."""
        return agent_operations.get_agent_info(self, reply_to)

    # ============================================================================
    # AI FUNCTIONS - Delegated to ai_functions module
    # ============================================================================

    def _resolve_agent_with_ai(self, user_input: str, agents: list) -> str:
        """Use AI reasoning to resolve which agent the user meant."""
        return ai_functions._resolve_agent_with_ai(self, user_input, agents)

    def _get_simple_completion(self, prompt: str) -> str:
        """Get a simple completion for agent resolution."""
        return ai_functions._get_simple_completion(self, prompt)

    def _load_system_prompt_instructions(self) -> str:
        """Load system prompt instructions from the runbook."""
        return ai_functions._load_system_prompt_instructions(self)

    def _execute_agent_function(self, function_name: str, function_args: str, reply_to: str) -> str:
        """Execute agent management functions like create_agent, delete_agent, manage_agents."""
        return ai_functions._execute_agent_function(self, function_name, function_args, reply_to)

    def _get_runbook_examples(self) -> str:
        """Get examples of existing agent runbooks with job titles and structures."""
        return ai_functions._get_runbook_examples(self)

    # ============================================================================
    # COLLABORATION - Delegated to collaboration module
    # ============================================================================

    def _collaborate_with_agents(self, task: str, agent_names: list, reply_to: str):
        """Collaborate with specific agents by delegating tasks and coordinating responses."""
        return collaboration._collaborate_with_agents(self, task, agent_names, reply_to)

    def _handle_agent_response(self, response_data: dict):
        """Handle responses from delegated agents."""
        return collaboration._handle_agent_response(self, response_data)

    def _handle_natural_agent_response(self, data: dict):
        """Handle natural conversation responses from other agents."""
        return collaboration._handle_natural_agent_response(self, data)

    def _synthesize_responses(self, original_query: str):
        """Synthesize multiple agent responses into a coherent final response."""
        return collaboration._synthesize_responses(self, original_query)

    def _check_collaboration_completion(self, from_agent: str, task_result: str, original_task: dict, user_topic: str):
        """Check if incoming agent response completes any active collaborations."""
        return collaboration._check_collaboration_completion(self, from_agent, task_result, original_task, user_topic)

    def _synthesize_collaboration_responses(self, collaboration: dict):
        """Synthesize multiple agent responses from a collaboration."""
        return collaboration._synthesize_collaboration_responses(self, collaboration)

    def _cleanup_timed_out_collaborations(self):
        """Clean up collaborations that have timed out."""
        return collaboration._cleanup_timed_out_collaborations(self)


def main():
    agent = AssistantAgent()
    agent.run()

if __name__ == "__main__":
    main()
