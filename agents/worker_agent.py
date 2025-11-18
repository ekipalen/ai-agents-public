"""
Unified Worker Agent - Generic agent runner for configurable worker agents.
This single file can run different types of worker agents based on configuration.
"""

import sys
import os
import time
import json
import re

# Add the project root to the path so we can import agentkit
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'agentkit'))

from agentkit import BaseAgent
from agentkit.runbook_loader import RunbookLoader
import argparse

print("--- [WORKER AGENT] Starting unified worker agent ---", flush=True)

class WorkerAgent(BaseAgent):
    """
    Generic worker agent that loads its behavior from runbooks.
    Can be used for researcher, synthesizer, data_analyst, etc.
    """

    def __init__(self, agent_type: str):
        print(f"--- [WORKER AGENT] Initializing {agent_type} ---", flush=True)

        try:
            # Load runbook from external markdown file
            runbooks_dir = os.path.join(os.path.dirname(__file__), '..', 'runbooks')
            loader = RunbookLoader(runbooks_dir)
            runbook = loader.load_runbook(agent_type)

            print(f"[WORKER AGENT] Successfully loaded runbook for {agent_type} with {len(runbook.capabilities)} capabilities")
            print(f"[WORKER AGENT] Role: {runbook.role[:100]}...")

        except Exception as e:
            print(f"[WORKER AGENT] Failed to load runbook for {agent_type}: {e}")
            print("[WORKER AGENT] Falling back to basic configuration...")

            # Fallback runbook if loading fails
            from agentkit import AgentRunbook, AgentCapability
            runbook = AgentRunbook(
                agent_name=agent_type,
                role=f"{agent_type.title()} agent with configurable capabilities",
                capabilities=[
                    AgentCapability(
                        name="task_processing",
                        description=f"Process tasks as a {agent_type} agent",
                        parameters={"task": "The task to process"},
                        example_usage=f"Handle {agent_type} tasks",
                        tags=[agent_type, "configurable"]
                    )
                ],
                collaboration_patterns=[f"{agent_type.title()} capabilities and collaboration patterns"],
                dependencies=[]
            )

        super().__init__(
            name=agent_type,
            role=runbook.role,
            runbook=runbook
        )

        self.agent_type = agent_type

    def _message_handler(self, message: dict):
        """
        Handle incoming messages and process tasks.
        Generic handler that works for any worker agent type.
        """
        print(f"[{self.agent_type.upper()}] Received message on topic {message['channel']}", flush=True)

        try:
            # Use the parsed data from the base class, with fallback
            data = message.get('parsed_data')
            if data is None:
                raw_data = message['data'].decode()
                try:
                    data = json.loads(raw_data)
                    print(f"[{self.agent_type.upper()}] Manually parsed JSON: {type(data)}", flush=True)
                except json.JSONDecodeError:
                    data = raw_data
                    print(f"[{self.agent_type.upper()}] Plain text message: {data[:100]}", flush=True)

            print(f"[{self.agent_type.upper()}] Message data type: {type(data)}", flush=True)

            # Handle different types of collaboration messages
            if isinstance(data, dict):
                # Check if this is a wrapped message with 'messages' field (from invoke endpoint)
                if "messages" in data and isinstance(data["messages"], list) and len(data["messages"]) > 0:
                    # Extract the actual message content from the messages array
                    user_message = data["messages"][0].get("content", "")
                    try:
                        # Try to parse the content as JSON (our collaboration messages)
                        content_data = json.loads(user_message)
                        collaboration_type = content_data.get("collaboration_type")
                        print(f"[{self.agent_type.upper()}] Extracted collaboration message: {collaboration_type}", flush=True)
                        data = content_data  # Use the extracted data
                    except (json.JSONDecodeError, TypeError):
                        print(f"[{self.agent_type.upper()}] Message content is not JSON collaboration message", flush=True)

                collaboration_type = data.get("collaboration_type")

                if collaboration_type == "request":
                    print(f"[{self.agent_type.upper()}] Handling collaboration request", flush=True)
                    self._handle_collaboration_request(data)
                elif collaboration_type == "offer":
                    print(f"[{self.agent_type.upper()}] Handling collaboration offer", flush=True)
                    self._handle_collaboration_offer(data)
                elif collaboration_type == "context_share":
                    print(f"[{self.agent_type.upper()}] Handling context share", flush=True)
                    self._handle_context_share(data)
                elif collaboration_type == "negotiation":
                    print(f"[{self.agent_type.upper()}] Handling negotiation", flush=True)
                    self._handle_negotiation(data)
                elif collaboration_type == "status_query":
                    print(f"[{self.agent_type.upper()}] Handling status query", flush=True)
                    self._handle_status_query(data)
                elif collaboration_type == "workflow_coordination":
                    print(f"[{self.agent_type.upper()}] Handling workflow coordination", flush=True)
                    self._handle_workflow_coordination(data)
                elif collaboration_type == "request_response":
                    print(f"[{self.agent_type.upper()}] Handling collaboration response", flush=True)
                    self._handle_collaboration_response(data)
                elif collaboration_type == "offer_response":
                    print(f"[{self.agent_type.upper()}] Handling offer response", flush=True)
                    self._handle_offer_response(data)
                elif collaboration_type == "collaboration_result":
                    print(f"[{self.agent_type.upper()}] Handling collaboration result", flush=True)
                    self._handle_collaboration_result(data)
                elif collaboration_type == "negotiation_response":
                    print(f"[{self.agent_type.upper()}] Handling negotiation response", flush=True)
                    self._handle_negotiation_response(data)
                elif collaboration_type == "context_acknowledgment":
                    print(f"[{self.agent_type.upper()}] Handling context acknowledgment", flush=True)
                    self._handle_context_acknowledgment(data)
                elif collaboration_type == "status_response":
                    print(f"[{self.agent_type.upper()}] Handling status response", flush=True)
                    self._handle_status_response(data)
                elif collaboration_type == "workflow_acknowledgment":
                    print(f"[{self.agent_type.upper()}] Handling workflow acknowledgment", flush=True)
                    self._handle_workflow_acknowledgment(data)
                elif collaboration_type == "natural_conversation":
                    print(f"[{self.agent_type.upper()}] Handling natural conversation", flush=True)
                    self._handle_natural_conversation(data)

                else:
                    # Check if this is a user message with "messages" array (from @mention routing)
                    if "messages" in data and isinstance(data.get("messages"), list):
                        print(f"[{self.agent_type.upper()}] Handling user message with messages array", flush=True)
                        natural_data = {
                            "collaboration_type": "natural_conversation",
                            "from_agent": "user",  # User messages via @mention
                            "messages": data["messages"],  # Pass through the messages array
                            "context": "user_mention",
                            "timestamp": time.time(),
                            "reply_to": data.get("reply_to", "user_session:main")
                        }
                        self._handle_natural_conversation(natural_data)
                    # PURE NATURAL APPROACH: Convert legacy tasks to natural conversations
                    elif "from_agent" in data and "task" in data:
                        print(f"[{self.agent_type.upper()}] Converting legacy task message to natural conversation", flush=True)
                        message_text = f"{data.get('from_agent', 'Assistant')} asks: {data['task']}"
                        natural_data = {
                            "collaboration_type": "natural_conversation",
                            "from_agent": data.get("from_agent", "unknown"),
                            "message": message_text,
                            "context": "converted_legacy_task",
                            "timestamp": time.time(),
                            "reply_to": data.get("reply_to", "user_session:main")
                        }
                        self._handle_natural_conversation(natural_data)
                    else:
                        print(f"[{self.agent_type.upper()}] Unknown message format, converting to string", flush=True)
                        message_text = str(data)
                        natural_data = {
                            "collaboration_type": "natural_conversation",
                            "from_agent": data.get("from_agent", "unknown"),
                            "message": message_text,
                            "context": "unknown_format",
                            "timestamp": time.time(),
                            "reply_to": data.get("reply_to", "user_session:main")
                        }
                        self._handle_natural_conversation(natural_data)
            else:
                print(f"[{self.agent_type.upper()}] Received non-dict message: {data}", flush=True)

        except Exception as e:
            print(f"[{self.agent_type.upper()}] An error occurred: {e}", flush=True)
            import traceback
            traceback.print_exc()

    def _handle_task(self, task_data: dict):
        """
        Handle a task assigned by another agent.
        Generic task handler that uses runbook capabilities for context.
        """
        from_agent = task_data.get("from_agent")
        task = task_data.get("task", {})
        user_topic = task_data.get("user_topic", "user_session:main")

        print(f"[{self.agent_type.upper()}] Received task from {from_agent}: {task.get('task', '')[:100]}...")

        try:
            # Extract task description
            task_description = task.get("task", "No task description provided")

            # Use AI to perform the task based on capabilities
            result = self._perform_task_with_capabilities(task_description)

            # Send result back to requesting agent
            response_data = {
                "from_agent": self.agent_type,
                "task_result": result,
                "original_task": task,
                "user_topic": user_topic
            }

            # Send to the requesting agent
            self.send_message(f"agent:{from_agent}:inbox", response_data)

            print(f"[{self.agent_type.upper()}] Completed task and sent results back to {from_agent}")

        except Exception as e:
            print(f"[{self.agent_type.upper()}] Error processing task: {e}")
            # Send error response
            error_response = {
                "from_agent": self.agent_type,
                "task_result": f"Error during task processing: {str(e)}",
                "original_task": task,
                "user_topic": user_topic
            }
            self.send_message(f"agent:{from_agent}:inbox", error_response)

    # ===== ENHANCED COLLABORATION HANDLERS =====

    def _handle_collaboration_request(self, request_data: dict):
        """Handle a collaboration request from another agent."""
        from_agent = request_data.get("from_agent")
        collaboration_id = request_data.get("collaboration_id")
        task_description = request_data.get("task_description")
        priority = request_data.get("priority", "normal")
        context = request_data.get("context", {})

        print(f"[{self.agent_type.upper()}] Collaboration request from {from_agent} (ID: {collaboration_id})")
        print(f"[{self.agent_type.upper()}] Task: {task_description}")
        print(f"[{self.agent_type.upper()}] Priority: {priority}")

        # Use AI to decide whether to accept the collaboration request
        decision_prompt = f"""
        Another agent ({from_agent}) is requesting your collaboration on: {task_description}

        Context provided: {context}
        Priority: {priority}

        Your role: {self.runbook.role if hasattr(self, 'runbook') else 'Worker agent'}
        Your capabilities: {[cap.name for cap in self.runbook.capabilities] if hasattr(self, 'runbook') else []}

        Should you accept this collaboration request? Consider:
        1. Does this align with your capabilities?
        2. Do you have capacity to help?
        3. Is the priority appropriate?

        Respond with either "ACCEPT" or "DECLINE" followed by a brief explanation.
        """

        response = self.get_completion(
            messages=[{"role": "user", "content": decision_prompt}],
            system_prompt="You are a collaborative AI agent deciding whether to accept collaboration requests."
        )

        # Parse the decision
        if response and "ACCEPT" in response.upper():
            # Accept the collaboration
            self._accept_collaboration_request(request_data)
        else:
            # Decline the collaboration
            self._decline_collaboration_request(request_data, response or "Unable to process request")

    def _accept_collaboration_request(self, request_data: dict):
        """Accept a collaboration request and start working on it."""
        from_agent = request_data.get("from_agent")
        collaboration_id = request_data.get("collaboration_id")
        task_description = request_data.get("task_description")

        # Send acceptance response
        response_data = {
            "collaboration_type": "request_response",
            "collaboration_id": collaboration_id,
            "from_agent": self.agent_type,
            "response": "accepted",
            "message": f"I'll help with: {task_description}",
            "timestamp": time.time()
        }

        self.send_message(f"agent:{from_agent}:inbox", json.dumps(response_data))

        # Process the task
        result = self._perform_task_with_capabilities(task_description)

        # Send the result
        result_data = {
            "collaboration_type": "collaboration_result",
            "collaboration_id": collaboration_id,
            "from_agent": self.agent_type,
            "result": result,
            "timestamp": time.time()
        }

        self.send_message(f"agent:{from_agent}:inbox", json.dumps(result_data))
        print(f"[{self.agent_type.upper()}] Accepted and completed collaboration {collaboration_id}")

    def _decline_collaboration_request(self, request_data: dict, reason: str):
        """Decline a collaboration request."""
        from_agent = request_data.get("from_agent")
        collaboration_id = request_data.get("collaboration_id")

        response_data = {
            "collaboration_type": "request_response",
            "collaboration_id": collaboration_id,
            "from_agent": self.agent_type,
            "response": "declined",
            "reason": reason,
            "timestamp": time.time()
        }

        self.send_message(f"agent:{from_agent}:inbox", json.dumps(response_data))
        print(f"[{self.agent_type.upper()}] Declined collaboration {collaboration_id}: {reason}")

    def _handle_collaboration_offer(self, offer_data: dict):
        """Handle a collaboration offer from another agent."""
        from_agent = offer_data.get("from_agent")
        offer_id = offer_data.get("offer_id")
        offer_description = offer_data.get("offer_description")
        capabilities_offered = offer_data.get("capabilities_offered", [])

        print(f"[{self.agent_type.upper()}] Collaboration offer from {from_agent} (ID: {offer_id})")
        print(f"[{self.agent_type.upper()}] Offer: {offer_description}")

        # Decide whether to accept the offer
        decision_prompt = f"""
        Another agent ({from_agent}) is offering to collaborate with you on: {offer_description}

        Capabilities offered: {capabilities_offered}
        Your current capabilities: {[cap.name for cap in self.runbook.capabilities] if hasattr(self, 'runbook') else []}

        Would this collaboration be beneficial for your current work?
        Consider if you need help with any tasks that match these capabilities.

        Respond with either "ACCEPT" or "DECLINE" followed by a brief explanation.
        """

        response = self.get_completion(
            messages=[{"role": "user", "content": decision_prompt}],
            system_prompt="You are a collaborative AI agent deciding whether to accept collaboration offers."
        )

        # Parse the decision
        if response and "ACCEPT" in response.upper():
            self._accept_collaboration_offer(offer_data)
        else:
            self._decline_collaboration_offer(offer_data, response or "Not needed at this time")

    def _accept_collaboration_offer(self, offer_data: dict):
        """Accept a collaboration offer."""
        from_agent = offer_data.get("from_agent")
        offer_id = offer_data.get("offer_id")

        response_data = {
            "collaboration_type": "offer_response",
            "offer_id": offer_id,
            "from_agent": self.agent_type,
            "response": "accepted",
            "message": "I would appreciate your help",
            "timestamp": time.time()
        }

        self.send_message(f"agent:{from_agent}:inbox", json.dumps(response_data))
        print(f"[{self.agent_type.upper()}] Accepted collaboration offer {offer_id}")

    def _decline_collaboration_offer(self, offer_data: dict, reason: str):
        """Decline a collaboration offer."""
        from_agent = offer_data.get("from_agent")
        offer_id = offer_data.get("offer_id")

        response_data = {
            "collaboration_type": "offer_response",
            "offer_id": offer_id,
            "from_agent": self.agent_type,
            "response": "declined",
            "reason": reason,
            "timestamp": time.time()
        }

        self.send_message(f"agent:{from_agent}:inbox", json.dumps(response_data))
        print(f"[{self.agent_type.upper()}] Declined collaboration offer {offer_id}: {reason}")

    def _handle_context_share(self, context_data: dict):
        """Handle context sharing from another agent."""
        from_agent = context_data.get("from_agent")
        context_type = context_data.get("context_type")
        context_info = context_data.get("context_data", {})
        collaboration_id = context_data.get("collaboration_id")

        print(f"[{self.agent_type.upper()}] Received {context_type} context from {from_agent}")

        # Store the context for future use
        if not hasattr(self, 'shared_contexts'):
            self.shared_contexts = {}

        context_key = f"{from_agent}_{collaboration_id or 'general'}"
        self.shared_contexts[context_key] = {
            "context_type": context_type,
            "data": context_info,
            "timestamp": time.time()
        }

        # Acknowledge receipt
        response_data = {
            "collaboration_type": "context_acknowledgment",
            "from_agent": self.agent_type,
            "original_from": from_agent,
            "context_type": context_type,
            "message": f"Received and stored {context_type} context",
            "timestamp": time.time()
        }

        self.send_message(f"agent:{from_agent}:inbox", json.dumps(response_data))

    def _handle_negotiation(self, negotiation_data: dict):
        """Handle a collaboration negotiation."""
        from_agent = negotiation_data.get("from_agent")
        negotiation_id = negotiation_data.get("negotiation_id")
        proposal = negotiation_data.get("proposal", {})
        counter_offers = negotiation_data.get("counter_offers", [])

        print(f"[{self.agent_type.upper()}] Negotiation started by {from_agent} (ID: {negotiation_id})")

        # Use AI to evaluate the proposal and respond
        negotiation_prompt = f"""
        Another agent ({from_agent}) is proposing collaboration terms:
        {proposal}

        Counter offers provided: {counter_offers}

        Your capabilities: {[cap.name for cap in self.runbook.capabilities] if hasattr(self, 'runbook') else []}

        Evaluate this proposal and decide how to respond. Consider:
        1. Are the terms fair and beneficial?
        2. Do you have the capacity for this work?
        3. Should you counter-offer or accept/decline?

        Respond with your decision and any counter-proposals.
        """

        response = self.get_completion(
            messages=[{"role": "user", "content": negotiation_prompt}],
            system_prompt="You are negotiating collaboration terms with another AI agent."
        )

        # Send negotiation response
        response_data = {
            "collaboration_type": "negotiation_response",
            "negotiation_id": negotiation_id,
            "from_agent": self.agent_type,
            "response": response or "Evaluating proposal...",
            "timestamp": time.time()
        }

        self.send_message(f"agent:{from_agent}:inbox", json.dumps(response_data))

    def _handle_status_query(self, query_data: dict):
        """Handle a status query from another agent."""
        from_agent = query_data.get("from_agent")

        # Prepare status information
        status_info = {
            "agent_name": self.agent_type,
            "status": "active",
            "capabilities": [cap.name for cap in self.runbook.capabilities] if hasattr(self, 'runbook') else [],
            "current_tasks": len(getattr(self, 'active_tasks', [])),
            "collaboration_history": len(getattr(self, 'collaboration_history', [])),
            "timestamp": time.time()
        }

        response_data = {
            "collaboration_type": "status_response",
            "from_agent": self.agent_type,
            "query_from": from_agent,
            "status_info": status_info,
            "timestamp": time.time()
        }

        self.send_message(f"agent:{from_agent}:inbox", json.dumps(response_data))
        print(f"[{self.agent_type.upper()}] Responded to status query from {from_agent}")

    def _handle_workflow_coordination(self, workflow_data: dict):
        """Handle workflow coordination from another agent."""
        from_agent = workflow_data.get("from_agent")
        workflow_id = workflow_data.get("workflow_id")
        workflow_definition = workflow_data.get("workflow_definition", {})
        participating_agents = workflow_data.get("participating_agents", [])

        print(f"[{self.agent_type.upper()}] Joined workflow {workflow_id} coordinated by {from_agent}")
        print(f"[{self.agent_type.upper()}] Participants: {participating_agents}")

        # Acknowledge participation
        response_data = {
            "collaboration_type": "workflow_acknowledgment",
            "workflow_id": workflow_id,
            "from_agent": self.agent_type,
            "status": "joined",
            "message": f"Ready to participate in workflow as {self.agent_type}",
            "timestamp": time.time()
        }

        self.send_message(f"agent:{from_agent}:inbox", json.dumps(response_data))

        # Store workflow information for coordination
        if not hasattr(self, 'active_workflows'):
            self.active_workflows = {}

        self.active_workflows[workflow_id] = {
            "coordinator": from_agent,
            "definition": workflow_definition,
            "participants": participating_agents,
            "joined_at": time.time()
        }

    # ===== RESPONSE HANDLER METHODS =====

    def _handle_collaboration_response(self, response_data: dict):
        """Handle response to a collaboration request."""
        from_agent = response_data.get("from_agent")
        collaboration_id = response_data.get("collaboration_id")
        response = response_data.get("response")
        message = response_data.get("message", "")

        print(f"[{self.agent_type.upper()}] Collaboration response from {from_agent}: {response}")
        if response == "accepted":
            print(f"[{self.agent_type.upper()}] ✅ {from_agent} accepted collaboration {collaboration_id}")
        else:
            print(f"[{self.agent_type.upper()}] ❌ {from_agent} declined collaboration {collaboration_id}: {message}")

    def _handle_offer_response(self, response_data: dict):
        """Handle response to a collaboration offer."""
        from_agent = response_data.get("from_agent")
        offer_id = response_data.get("offer_id")
        response = response_data.get("response")
        message = response_data.get("message", "")

        print(f"[{self.agent_type.upper()}] Offer response from {from_agent}: {response}")
        if response == "accepted":
            print(f"[{self.agent_type.upper()}] ✅ {from_agent} accepted offer {offer_id}")
        else:
            print(f"[{self.agent_type.upper()}] ❌ {from_agent} declined offer {offer_id}: {message}")

    def _handle_collaboration_result(self, result_data: dict):
        """Handle the result of a collaboration task."""
        from_agent = result_data.get("from_agent")
        collaboration_id = result_data.get("collaboration_id")
        result = result_data.get("result", "")

        print(f"[{self.agent_type.upper()}] Collaboration result from {from_agent} (ID: {collaboration_id})")
        print(f"[{self.agent_type.upper()}] Result preview: {result[:200]}...")

        # Store the result for future reference
        if not hasattr(self, 'collaboration_results'):
            self.collaboration_results = {}

        self.collaboration_results[collaboration_id] = {
            "from_agent": from_agent,
            "result": result,
            "timestamp": time.time()
        }

        print(f"[{self.agent_type.upper()}] ✅ Stored collaboration result {collaboration_id}")

    def _handle_negotiation_response(self, response_data: dict):
        """Handle response to a negotiation."""
        from_agent = response_data.get("from_agent")
        negotiation_id = response_data.get("negotiation_id")
        response = response_data.get("response", "")

        print(f"[{self.agent_type.upper()}] Negotiation response from {from_agent} (ID: {negotiation_id})")
        print(f"[{self.agent_type.upper()}] Response: {response[:100]}...")

    def _handle_context_acknowledgment(self, ack_data: dict):
        """Handle acknowledgment of context sharing."""
        from_agent = ack_data.get("from_agent")
        original_from = ack_data.get("original_from")
        context_type = ack_data.get("context_type")
        message = ack_data.get("message", "")

        print(f"[{self.agent_type.upper()}] Context acknowledgment from {from_agent}")
        print(f"[{self.agent_type.upper()}] {message}")

    def _handle_status_response(self, status_data: dict):
        """Handle status response from another agent."""
        from_agent = status_data.get("from_agent")
        query_from = status_data.get("query_from")
        status_info = status_data.get("status_info", {})

        print(f"[{self.agent_type.upper()}] Status response from {from_agent}")
        print(f"[{self.agent_type.upper()}] Status: {status_info.get('status')}")
        print(f"[{self.agent_type.upper()}] Active tasks: {status_info.get('current_tasks', 0)}")

    def _handle_workflow_acknowledgment(self, ack_data: dict):
        """Handle workflow coordination acknowledgment."""
        from_agent = ack_data.get("from_agent")
        workflow_id = ack_data.get("workflow_id")
        status = ack_data.get("status")
        message = ack_data.get("message", "")

        print(f"[{self.agent_type.upper()}] Workflow acknowledgment from {from_agent}")
        print(f"[{self.agent_type.upper()}] Workflow {workflow_id}: {status}")
        print(f"[{self.agent_type.upper()}] {message}")

    def _handle_natural_conversation(self, conversation_data: dict):
        """Handle natural, conversational messages from other agents."""
        from_agent = conversation_data.get("from_agent")

        # Handle both simple message format and messages array format
        message = ""
        messages_array = None  # Keep full conversation history

        if "messages" in conversation_data:
            # Handle messages array format (from assistant)
            messages_array = conversation_data.get("messages", [])
            if messages_array and isinstance(messages_array, list):
                # Get the latest user message for logging, but keep full history
                for msg in reversed(messages_array):
                    if isinstance(msg, dict) and msg.get("role") == "user":
                        message = msg.get("content", "")
                        break
                if not message and messages_array:
                    # Fallback to last message if no user message found
                    last_msg = messages_array[-1]
                    if isinstance(last_msg, dict):
                        message = last_msg.get("content", "")
        else:
            # Handle simple message format
            message = conversation_data.get("message", "")

        context = conversation_data.get("context", "")
        reply_to = conversation_data.get("reply_to")
        timestamp = conversation_data.get("timestamp", 0)
        original_user_topic = conversation_data.get("original_user_topic")

        # Check if message is from before agent startup (ignore old queued messages)
        if timestamp > 0 and timestamp < self.startup_time:
            print(f"[{self.agent_type.upper()}] Ignoring old message from {from_agent} (timestamp: {timestamp:.1f}, startup: {self.startup_time:.1f})", flush=True)
            return

        # Simple message deduplication to prevent processing duplicate messages
        message_hash = hash((from_agent + message + context).strip().lower())

        # Initialize deduplication tracking if needed
        if not hasattr(self, '_recent_messages'):
            self._recent_messages = {}

        current_time = time.time()

        # Check if we've seen this message recently (within last 5 seconds)
        if message_hash in self._recent_messages:
            last_seen = self._recent_messages[message_hash]
            if current_time - last_seen < 5:  # 5 second window - enough to catch loops, short enough for repeat requests
                print(f"[{self.agent_type.upper()}] Ignoring duplicate message from {from_agent} (hash: {message_hash})", flush=True)
                return

        # Update the tracking
        self._recent_messages[message_hash] = current_time

        # Clean up old entries (keep only last 50 messages)
        if len(self._recent_messages) > 50:
            oldest_key = min(self._recent_messages.keys(), key=self._recent_messages.get)
            del self._recent_messages[oldest_key]

        print(f"[{self.agent_type.upper()}] Natural conversation from {from_agent}")
        print(f"[{self.agent_type.upper()}] Extracted message: '{message}'")
        print(f"[{self.agent_type.upper()}] Original user topic: '{original_user_topic}'")
        if context:
            print(f"[{self.agent_type.upper()}] Context: {context}")
        print(f"[{self.agent_type.upper()}] Full conversation data keys: {list(conversation_data.keys())}")

        # SIMPLE APPROACH: No complex loop prevention - just respond to messages

        # SIMPLE RESPONSE: Just respond based on sender type
        if self._is_assistant(from_agent):
            # Direct response to assistant - keep it simple
            # Use full conversation history if available, otherwise just the message
            if messages_array:
                response = self._respond_to_assistant_with_history(messages_array, reply_to)
            else:
                response = self._respond_to_assistant(message)
        else:
            # Response to other agents - also simple
            response = self._respond_to_agent(from_agent, message)

        if response:
            # SIMPLE APPROACH: Just send the response
            self._send_natural_response(from_agent, response, context, reply_to, original_user_topic)
            print(f"[{self.agent_type.upper()}] Responded to {from_agent}: {response[:50]}...")

    # ===== DEMONSTRATION METHODS =====

    def demo_collaboration_features(self):
        """
        Demonstrate the enhanced collaboration features available to agents.
        Call this method to see examples of how agents can collaborate.
        """
        print(f"🤖 [{self.agent_type.upper()}] COLLABORATION FEATURES DEMO 🤖")

        print("\n📋 Available Enhanced Collaboration Methods:")
        print("1. request_collaboration(target, task, context, priority)")
        print("2. offer_collaboration(target, description, capabilities)")
        print("3. find_agents_by_capability(capability)")
        print("4. share_context(target, type, data)")
        print("5. query_agent_status(target)")
        print("6. negotiate_collaboration(target, proposal)")
        print("7. coordinate_workflow(definition, participants)")

        print("\n💡 Example Usage Scenarios:")

        # Dynamic help - works with any agent type
        print(f"\n🔧 {self.agent_type.title()} Collaboration Examples:")
        print("- Use natural language to collaborate with other agents")
        print("- The system automatically coordinates with available agents")
        print("- Example: 'Can you help me organize this data?'")

        print(f"\n✅ Demo complete for {self.agent_type} agent!")

    def test_direct_agent_communication(self):
        """
        Test direct communication with other agents to verify connectivity.
        """
        print(f"🧪 [{self.agent_type.upper()}] TESTING DIRECT AGENT COMMUNICATION")

        test_message = {
            "collaboration_type": "test_message",
            "from_agent": self.agent_type,
            "message": f"Hello from {self.agent_type}! Testing direct communication.",
            "timestamp": time.time(),
            "reply_to": self.inbox_topic
        }

        # Test communication with both agents
        # Dynamic targets - get available agents
        try:
            import requests
            response = requests.get("http://localhost:9000/agents", timeout=5)
            if response.status_code == 200:
                agents_data = response.json()
                targets = [agent['name'] for agent in agents_data if agent.get('status') == 'running' and agent['name'] != self.agent_type]
            else:
                targets = ["assistant"]  # fallback
        except Exception as e:
            print(f"[{self.agent_type.upper()}] Error discovering agents: {e}")
            targets = ["assistant"]  # fallback
        for target in targets:
            if target != self.agent_type:  # Don't send to ourselves
                print(f"📤 Sending test message to {target}...")
                self.send_message(f"agent:{target}:inbox", json.dumps(test_message))
                print(f"✅ Test message sent to {target}")

        print(f"🧪 Direct communication test complete for {self.agent_type}!")

    def _perform_task_with_capabilities(self, task_description: str) -> str:
        """
        Perform task using agent's capabilities from runbook.
        Generic method that works for any agent type.
        """
        # Build a MINIMAL system prompt - keep it concise
        system_prompt = f"""You are {self.agent_type}, {self.runbook.role if hasattr(self, 'runbook') else 'a specialized agent'}.

Focus on your core expertise and provide a clear, helpful response to the task."""

        # Use the AI completion system with the concise system prompt
        response = self.get_completion(
            messages=[{"role": "user", "content": task_description}],
            system_prompt=system_prompt
        )

        if response:
            return response
        else:
            return f"Error: Unable to process the task. Please check the task description and try again."





    def _respond_to_assistant(self, message: str) -> str:
        """Simple response to assistant messages using AI capabilities."""
        message_lower = message.lower()

        # Simple pattern matching for common assistant requests
        # Only match exact greetings, not messages that happen to contain greeting words
        if message_lower.strip() in ["hello", "hi", "greetings", "hey"] or message_lower.startswith("say hello"):
            return f"Hello! I'm {self.agent_type}, ready to help."
        elif "acknowledge" in message_lower and len(message_lower.split()) <= 3:
            return f"Acknowledged."

        # For any other request, use AI to understand and execute based on runbook
        return self._understand_and_execute_task(message)

    def _respond_to_assistant_with_history(self, messages: list, reply_to: str = None) -> str:
        """Respond to assistant with full conversation history for context."""
        # Get the latest user message for greeting check
        latest_message = ""
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "user":
                latest_message = msg.get("content", "")
                break

        # Simple pattern matching for common greetings
        message_lower = latest_message.lower()
        if message_lower.strip() in ["hello", "hi", "greetings", "hey"] or message_lower.startswith("say hello"):
            return f"Hello! I'm {self.agent_type}, ready to help."
        elif "acknowledge" in message_lower and len(message_lower.split()) <= 3:
            return f"Acknowledged."

        # For any other request, use AI with full conversation history
        return self._understand_and_execute_with_history(messages, reply_to)

    def _understand_and_execute_with_history(self, messages: list, reply_to: str = None) -> str:
        """Use AI to understand and execute tasks with full conversation history."""
        try:
            # Get the latest user message
            latest_message = ""
            for msg in reversed(messages):
                if isinstance(msg, dict) and msg.get("role") == "user":
                    latest_message = msg.get("content", "")
                    break

            # Check if this agent has actions that can handle the request
            if self.actions:
                print(f"[{self.agent_type.upper()}] Checking {len(self.actions)} available actions for potential match...", flush=True)

                # Use LLM to select the best action based on user intent
                best_action = self._select_action_with_llm(latest_message)

                # Execute the selected action if any
                if best_action:
                    action_name = best_action.get('name', '')
                    action_id = best_action.get('id', '')
                    print(f"[{self.agent_type.upper()}] Selected action: {action_name}", flush=True)

                    # Extract parameters from the message using AI
                    action_params = best_action.get('parameters', [])

                    if action_params:
                        # Action has parameters (required or optional) - try to extract them
                        extracted_params = self._extract_action_parameters(best_action, latest_message)

                        if extracted_params is not None:
                            # Send tool-calling indicator before executing
                            if reply_to:
                                self._send_tool_notification(reply_to, action_name, "executing")

                            print(f"[{self.agent_type.upper()}] Executing action: {action_name}", flush=True)
                            result = self.execute_action(action_id, extracted_params)

                            if result and result.get('result'):
                                return f"✅ {action_name} completed:\n\n{result['result']}"
                            elif result and result.get('error'):
                                return f"❌ Error executing {action_name}: {result['error']}"
                    else:
                        # No parameters at all - execute directly
                        # Send tool-calling indicator before executing
                        if reply_to:
                            self._send_tool_notification(reply_to, action_name, "executing")

                        print(f"[{self.agent_type.upper()}] Executing action: {action_name}", flush=True)
                        result = self.execute_action(action_id, {})

                        if result and result.get('result'):
                            return f"✅ {action_name} completed:\n\n{result['result']}"
                        elif result and result.get('error'):
                            return f"❌ Error executing {action_name}: {result['error']}"

            # Get agent capabilities from runbook
            capabilities = self._get_agent_capabilities()

            # Build actions section for AI if available
            actions_section = ""
            if self.actions:
                actions_section = "\n\nAvailable Actions:\n"
                for action in self.actions:
                    if action.get("enabled", True):
                        actions_section += f"- {action.get('name')}: {action.get('description')}\n"

            # Create a focused prompt for the AI
            system_prompt = f"""You are a {self.agent_type} agent.

Capabilities: {capabilities}{actions_section}

INSTRUCTIONS:
- Use the conversation history to provide contextual responses
- Execute tasks directly and provide helpful responses
- Be concise but complete - don't artificially limit response length
- Include relevant details when appropriate
- Stay focused on the specific task requested
- Keep responses natural and conversational
- NEVER mention ChatGPT, other AI systems, or external tools
- NEVER compare yourself to ChatGPT or other AI systems
- Focus on your specialized capabilities and the task at hand"""

            # Use the AI completion with full conversation history
            response = self.get_streaming_completion(
                messages=messages,  # Pass full conversation history
                system_prompt=system_prompt,
                functions=[]
            )

            if response:
                # Extract the final response from the streaming completion
                final_response = ""
                for chunk in response:
                    if chunk and not chunk.startswith("FUNC:"):
                        final_response += chunk

                if final_response.strip():
                    return final_response.strip()
                else:
                    return "I processed your request but have no response."
            else:
                return "Error: Unable to process the request. Please try again."

        except Exception as e:
            print(f"[{self.agent_type.upper()}] Error in _understand_and_execute_with_history: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return f"Error processing request: {str(e)}"

    def _select_action_with_llm(self, message: str) -> dict:
        """Use LLM to select the best action based on user intent."""
        try:
            # Build action list for LLM
            actions_desc = ""
            enabled_actions = [a for a in self.actions if a.get("enabled", True)]

            for i, action in enumerate(enabled_actions, 1):
                action_name = action.get('name', '')
                action_desc = action.get('description', '')
                action_id = action.get('id', '')
                actions_desc += f"{i}. {action_name} (ID: {action_id})\n   Description: {action_desc}\n\n"

            # Ask LLM to select best action
            selection_prompt = f"""You are an action selector. Given a user's message and a list of available actions, determine which action (if any) best matches the user's intent.

User message: "{message}"

Available actions:
{actions_desc}

Instructions:
1. Analyze the user's intent and what they're trying to accomplish
2. Compare against the available actions and their descriptions
3. Select the action that best matches the user's intent
4. If NO action matches well, return "NONE"
5. Return ONLY the action ID (e.g., "send-email" or "read-emails" or "NONE")

Return ONLY the action ID, nothing else."""

            ai_response = self.get_completion(
                messages=[{"role": "user", "content": selection_prompt}],
                system_prompt="You are an expert at understanding user intent and matching it to available actions."
            )

            if ai_response:
                selected_id = ai_response.strip().strip('"').strip("'")

                if selected_id == "NONE":
                    print(f"[{self.agent_type.upper()}] LLM determined no action matches the request", flush=True)
                    return None

                # Find the action by ID
                for action in enabled_actions:
                    if action.get('id') == selected_id:
                        print(f"[{self.agent_type.upper()}] LLM selected action: {action.get('name')} ({selected_id})", flush=True)
                        return action

                print(f"[{self.agent_type.upper()}] LLM returned unknown action ID: {selected_id}", flush=True)
                return None

            return None

        except Exception as e:
            print(f"[{self.agent_type.upper()}] Error selecting action with LLM: {e}", flush=True)
            return None

    def _extract_action_parameters(self, action: dict, message: str) -> dict:
        """Use AI to extract action parameters from user message."""
        try:
            action_params = action.get('parameters', [])
            if not action_params:
                return {}

            # Build parameter descriptions
            param_desc = ""
            for param in action_params:
                param_name = param.get('name', '')
                param_type = param.get('type', 'string')
                param_description = param.get('description', '')
                required = param.get('required', False)
                req_str = "required" if required else "optional"
                param_desc += f"- {param_name} ({param_type}, {req_str}): {param_description}\n"

            # Use AI to extract parameters
            extraction_prompt = f"""Extract parameters for the action "{action.get('name')}" from the user message.

User message: "{message}"

Available parameters:
{param_desc}

Instructions:
1. Read each parameter's description carefully to understand what value to extract
2. Extract values from the user message that match the parameter descriptions
3. Respect parameter types:
   - string: Extract text values as-is
   - number/integer: Extract numeric values (e.g., "5 items" → 5, "latest 10" → 10)
   - boolean: Convert yes/no/true/false to boolean
   - array: Extract list items if mentioned
4. For required parameters:
   - If explicitly mentioned in message, extract the value
   - If NOT mentioned but user is asking for test/mock/example/demo data, generate appropriate test value
   - Otherwise return "" (empty string)
5. For optional parameters:
   - Use "" (empty string) if not mentioned in the message
   - Only extract if explicitly stated
6. CRITICAL: Use "" for missing/unspecified parameters, NEVER null or None
7. Context awareness: If user says "send a test email" without specifying details, understand they want test data for the required fields

Return ONLY the JSON object with extracted parameters, nothing else."""

            ai_response = self.get_completion(
                messages=[{"role": "user", "content": extraction_prompt}],
                system_prompt="You are a parameter extraction specialist. Extract structured data from natural language."
            )

            if ai_response:
                # Try to parse JSON from response
                import json
                try:
                    params = json.loads(ai_response.strip())
                    # Convert None values to empty strings for Pydantic validation
                    params = {k: (v if v is not None else "") for k, v in params.items()}
                    print(f"[{self.agent_type.upper()}] Extracted parameters: {params}", flush=True)
                    return params
                except json.JSONDecodeError:
                    # Try to find JSON in the response
                    json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                    if json_match:
                        params = json.loads(json_match.group())
                        # Convert None values to empty strings for Pydantic validation
                        params = {k: (v if v is not None else "") for k, v in params.items()}
                        print(f"[{self.agent_type.upper()}] Extracted parameters from text: {params}", flush=True)
                        return params

            return None

        except Exception as e:
            print(f"[{self.agent_type.upper()}] Error extracting parameters: {e}", flush=True)
            return None

    def _send_tool_notification(self, reply_to: str, action_name: str, status: str):
        """Send a notification that a tool is being executed."""
        try:
            if status == "executing":
                message_content = f"🔧 Executing: {action_name}..."
            else:
                message_content = f"✅ {action_name} complete"

            # Send just the content - the base send_message method will wrap it properly
            import json
            self.send_message(reply_to, message_content)
            print(f"[{self.agent_type.upper()}] Sent tool notification: {status}", flush=True)
        except Exception as e:
            print(f"[{self.agent_type.upper()}] Failed to send tool notification: {e}", flush=True)

    def _understand_and_execute_task(self, task: str) -> str:
        """Use AI to understand and execute tasks based on agent capabilities."""
        try:
            # Get agent capabilities from runbook
            capabilities = self._get_agent_capabilities()

            # Create a focused prompt for the AI to understand and execute the task
            system_prompt = f"""You are a {self.agent_type} agent.

Capabilities: {capabilities}

TASK: {task}

INSTRUCTIONS:
- Execute this task directly and provide a helpful response
- Be concise but complete - don't artificially limit response length
- Include relevant details when appropriate
- Stay focused on the specific task requested
- Keep responses natural and conversational
- Natural self-introduction is OK when contextually appropriate
- NEVER mention ChatGPT, other AI systems, or external tools
- NEVER compare yourself to ChatGPT or other AI systems
- Focus on your specialized capabilities and the task at hand"""

            # Use the AI completion to understand and execute the task
            response = self.get_streaming_completion(
                messages=[{"role": "user", "content": task}],
                system_prompt=system_prompt,
                functions=[]
            )

            if response:
                # Extract the final response from the streaming completion
                final_response = ""
                for chunk in response:
                    if chunk and not chunk.startswith("FUNC:"):
                        final_response += chunk

                if final_response.strip():
                    return final_response.strip()

            # Fallback if AI completion fails
            return f"Understood. I'm {self.agent_type} and I'll help with that."

        except Exception as e:
            print(f"[{self.agent_type.upper()}] Error in task execution: {e}")
            return f"Understood. I'm {self.agent_type} and I'll help with that."

    def _get_agent_capabilities(self) -> str:
        """Get agent capabilities from the loaded runbook."""
        try:
            # Use the already-loaded runbook object instead of re-parsing the file
            if hasattr(self, 'runbook') and self.runbook and self.runbook.capabilities:
                capabilities_text = f"Role: {self.runbook.role}\n\nCore Capabilities:\n"
                for cap in self.runbook.capabilities:
                    capabilities_text += f"- {cap.name}"
                    if cap.description:
                        capabilities_text += f": {cap.description}"
                    capabilities_text += "\n"
                return capabilities_text.strip()

            # Fallback: Generic capabilities that work for any agent
            return f"Role: {self.agent_type.title()} agent\n\nCore Capabilities:\n- Task execution based on agent role\n- Information processing and analysis\n- Response generation\n- Problem solving within defined scope"

        except Exception as e:
            print(f"[{self.agent_type.upper()}] Error loading capabilities: {e}")
            return f"Role: {self.agent_type.title()} agent\n\nCore Capabilities:\n- General task execution\n- Information processing"

    def _is_assistant(self, sender_name: str) -> bool:
        """Check if the sender is the assistant agent or a user."""
        # The assistant is typically named "assistant", but we can make this more robust
        # Also treat "user" messages (from @mention routing) as assistant-like for proper AI responses
        return sender_name.lower() in ["assistant", "coordinator", "orchestrator", "user"]

    def _respond_to_agent(self, from_agent: str, message: str) -> str:
        """Simple response to other agent messages."""
        return f"Hello {from_agent}! This is {self.agent_type}. I received your message: {message[:50]}..."


    def _send_natural_response(self, to_agent: str, response: str, context: str, reply_to: str, original_user_topic: str = None):
        """Send a natural response message to another agent."""
        response_data = {
            "collaboration_type": "natural_conversation_response",
            "from_agent": self.agent_type,
            "original_from": to_agent,
            "response": response,
            "context": context,
            "timestamp": time.time(),
            "reply_to": reply_to
        }

        # Include original_user_topic if provided
        if original_user_topic:
            response_data["original_user_topic"] = original_user_topic

        success = self.send_message(f"agent:{to_agent}:inbox", json.dumps(response_data))
        if success:
            print(f"[{self.agent_type.upper()}] Sent natural response to {to_agent}")
        else:
            print(f"[{self.agent_type.upper()}] Failed to send response to {to_agent}")

        # Also send to the reply_to topic if it's different from the agent
        # For user_session topics, send just the response text (agentkit will add sender/timestamp)
        if reply_to and reply_to != f"agent:{to_agent}:inbox":
            if reply_to.startswith("user_session:"):
                # Send plain text response for user-facing topics
                print(f"[{self.agent_type.upper()}] Sending to {reply_to}: {response[:50]}...")
                self.send_message(reply_to, response)
            else:
                # Send structured collaboration data for agent-to-agent topics
                print(f"[{self.agent_type.upper()}] Sending structured response to {reply_to}")
                self.send_message(reply_to, json.dumps(response_data))


def main():
    """Main entry point for the worker agent."""
    parser = argparse.ArgumentParser(description='Run a unified worker agent')
    parser.add_argument('agent_type', help='Type of agent to run (any agent name)')
    args = parser.parse_args()

    print(f"--- [WORKER AGENT] Starting {args.agent_type} agent ---", flush=True)

    try:
        agent = WorkerAgent(args.agent_type)
        print(f"--- [WORKER AGENT] {args.agent_type} agent initialized, starting run loop ---", flush=True)
        agent.run()
    except KeyboardInterrupt:
        print(f"--- [WORKER AGENT] {args.agent_type} agent shutting down ---", flush=True)
    except Exception as e:
        print(f"--- [WORKER AGENT] Error running {args.agent_type} agent: {e} ---", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
