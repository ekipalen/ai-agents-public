"""
Multi-agent collaboration module for the Assistant Agent.

This module handles all collaboration logic including:
- Delegating tasks to multiple agents
- Managing collaboration state and timeouts
- Processing agent responses
- Synthesizing multi-agent responses into coherent answers
- Natural conversation handling between agents
"""

import json
import time


def _collaborate_with_agents(self, task: str, agent_names: list, reply_to: str):
    """
    Collaborate with specific agents by delegating tasks and coordinating responses.

    Args:
        self: The agent instance
        task: The task to delegate to agents
        agent_names: List of agent names to collaborate with
        reply_to: The topic to send responses back to
    """
    print(f"[DEBUG] Collaborating with agents {agent_names} on task: '{task}'")
    try:
        # Get current agent status
        agents_info = self.discover_all_agents()
        if not agents_info:
            self.send_message(reply_to, "❌ Unable to discover agents for collaboration.")
            return

        # Check which requested agents are available and running
        available_agents = []
        unavailable_agents = []

        print(f"[DEBUG] Looking for agents: {agent_names}")
        print(f"[DEBUG] Found agents info: {[a['name'] + '(' + ('running' if a.get('is_running') else 'stopped') + ')' for a in agents_info]}")

        for agent_name in agent_names:
            agent_info = next((a for a in agents_info if a['name'].lower() == agent_name.lower()), None)
            print(f"[DEBUG] Agent {agent_name}: info={agent_info is not None}, running={agent_info.get('is_running') if agent_info else 'N/A'}")
            if agent_info and agent_info.get('is_running'):
                available_agents.append(agent_info)
            else:
                unavailable_agents.append(agent_name)

        if unavailable_agents:
            self.send_message(reply_to, f"⚠️ The following agents are not available: {', '.join(unavailable_agents)}")

        if not available_agents:
            self.send_message(reply_to, "❌ No requested agents are currently available for collaboration.")
            return

        # Start collaboration
        self.send_message(reply_to, f"🤝 Starting collaboration with {len(available_agents)} agent(s): {', '.join([a['name'] for a in available_agents])}")

        # Delegate tasks to each available agent
        responses = {}
        for agent_info in available_agents:
            agent_name = agent_info['name']
            self.send_message(reply_to, f"📤 Sending task to {agent_name}...")

            # Create task data
            capabilities = agent_info.get('capabilities', [])
            if not capabilities:
                capabilities = ['general']

            task_data = {
                "from_agent": "assistant",
                "task": {
                    "task": task,
                    "agent_type": capabilities[0],
                    "priority": 5,
                    "subtask_index": 0,
                    "total_subtasks": 1
                },
                "user_topic": reply_to,
                "original_query": task
            }

            # Send task to agent
            try:
                self.send_message(f"agent:{agent_name}:inbox", task_data)
                responses[agent_name] = "waiting"
                print(f"[DEBUG] Sent task to {agent_name}")
            except Exception as e:
                print(f"[DEBUG] Failed to send task to {agent_name}: {e}")
                responses[agent_name] = f"Error: {str(e)}"

        # Set up expectations for responses (non-blocking)
        # The message handler will process responses asynchronously
        self.send_message(reply_to, f"📤 All tasks sent! Waiting for agent responses...")

        # Store collaboration state for the message handler to track
        collaboration_key = f"collaboration_{task}_{reply_to}"
        if not hasattr(self, 'active_collaborations'):
            self.active_collaborations = {}

        self.active_collaborations[collaboration_key] = {
            "task": task,
            "expected_agents": [agent['name'] for agent in available_agents],
            "received_responses": [],
            "user_topic": reply_to,
            "start_time": time.time(),
            "timeout": 30  # 30 seconds
        }

        # Don't block - let the message handler process responses asynchronously
        # The collaboration will complete when all responses are received or timeout occurs

    except Exception as e:
        print(f"[DEBUG] Error in _collaborate_with_agents: {e}")
        import traceback
        traceback.print_exc()
        self.send_message(reply_to, f"Sorry, there was an error setting up collaboration: {str(e)}")


def _handle_agent_response(self, response_data: dict):
    """
    Handle responses from delegated agents.

    Processes task results from agents and manages the synthesis of multiple
    responses when all agents have completed their tasks.

    Args:
        self: The agent instance
        response_data: Dictionary containing agent response data including:
            - from_agent: Name of the responding agent
            - task_result: The agent's response content
            - original_task: The original task details
            - user_topic: Topic to send responses back to
    """
    from_agent = response_data.get("from_agent")
    task_result = response_data.get("task_result")
    original_task = response_data.get("original_task", {})
    user_topic = response_data.get("user_topic", "user_session:main")  # Default fallback

    print(f"Received response from {from_agent}: {task_result[:100]}...")

    # Store the result for potential synthesis
    if not hasattr(self, 'pending_responses'):
        self.pending_responses = {}

    # Use the full task description as the key for better matching
    task_description = original_task.get('task', '')
    task_key = f"{task_description}_{original_task.get('subtask_index', 0)}"

    self.pending_responses[task_key] = {
        "from_agent": from_agent,
        "result": task_result,
        "task": original_task,
        "user_topic": user_topic
    }

    # Check if this response completes any active collaborations
    _check_collaboration_completion(self, from_agent, task_result, original_task, user_topic)

    # Also check for timed-out collaborations
    _cleanup_timed_out_collaborations(self)

    # Get total subtasks for this task
    total_subtasks = original_task.get("total_subtasks", 1)

    # Provide minimal feedback about received response (only for complex tasks)
    if total_subtasks > 1:  # Only show completion for multi-agent tasks
        self.send_message(user_topic, f"✅ {from_agent.title()} completed their task")

    # Check if we have all responses for this task
    current_task = original_task.get('task', '')
    subtask_index = original_task.get('subtask_index', 0)

    # Count responses for this specific subtask
    completed_responses = 0
    for key, response_data in self.pending_responses.items():
        stored_task = response_data.get('task', {}).get('task', '')
        stored_index = response_data.get('task', {}).get('subtask_index', -1)
        if stored_task == current_task and stored_index == subtask_index:
            completed_responses = 1  # This specific subtask is complete
            break

    # Check if ALL subtasks are complete by counting unique subtask indices
    # Group responses by their subtask index
    found_indices = set()
    for key, response_data in self.pending_responses.items():
        stored_index = response_data.get('task', {}).get('subtask_index', -1)
        if stored_index >= 0:
            found_indices.add(stored_index)

    all_subtasks_complete = len(found_indices) >= total_subtasks
    print(f"[DEBUG] Completion check: found {len(found_indices)}/{total_subtasks} subtasks, complete: {all_subtasks_complete}")

    # Send progress update about completion status
    if all_subtasks_complete:
        # Start synthesis process
        print(f"All {total_subtasks} responses received, starting synthesis...", flush=True)
        # Find the original user query from any response
        original_query = None
        for response_data in self.pending_responses.values():
            if response_data.get('task', {}).get('original_query'):
                original_query = response_data['task']['original_query']
                break
        if not original_query:
            # Fallback to the current task description
            original_query = original_task.get('task', '')
        _synthesize_responses(self, original_query)


def _handle_natural_agent_response(self, data: dict):
    """
    Handle natural conversation responses from other agents.

    Processes conversational messages from agents and forwards them to the user,
    maintaining conversation history for context continuity.

    Args:
        self: The agent instance
        data: Dictionary containing:
            - from_agent: Name of the responding agent
            - message/response: The agent's response content
            - original_user_topic: Topic to send the response to
            - timestamp: When the message was sent
    """
    from_agent = data.get("from_agent")
    # Try both "message" and "response" fields (worker agents use "response")
    message = data.get("message") or data.get("response", "")
    original_from = data.get("original_from", "")
    timestamp = data.get("timestamp", 0)
    user_topic = data.get("original_user_topic")
    if not user_topic:
        print(f"  [ASSISTANT] ERROR: Missing 'original_user_topic' in natural agent response from {from_agent}. Cannot forward to user.")
        return

    # Check if message is from before agent startup (ignore old queued messages)
    if timestamp > 0 and timestamp < self.startup_time:
        print(f"[ASSISTANT] Ignoring old message from {from_agent} (timestamp: {timestamp:.1f}, startup: {self.startup_time:.1f})", flush=True)
        return

    print(f"[ASSISTANT] Received natural response from {from_agent}: {message[:50]}...", flush=True)
    print(f"[ASSISTANT] Original user topic received: '{user_topic}'", flush=True)

    # Update conversation history with the agent's response
    if from_agent and message:
        if from_agent not in self.agent_conversations:
            self.agent_conversations[from_agent] = []
        self.agent_conversations[from_agent].append({"role": "assistant", "content": message})

    # Send the agent response back to the user
    formatted_response = f"{from_agent.title()}: {message}"

    self.send_message(user_topic, formatted_response)
    print(f"[ASSISTANT] Forwarded {from_agent} response to user on topic {user_topic}", flush=True)


def _synthesize_responses(self, original_query: str):
    """
    Synthesize multiple agent responses into a coherent final response.

    Combines responses from multiple agents into a comprehensive, well-structured
    answer using AI synthesis. Sends the synthesized response to the user.

    Args:
        self: The agent instance
        original_query: The original user query that triggered the multi-agent task
    """
    # Find all responses for this specific original query
    task_responses = {}
    for key, response_data in self.pending_responses.items():
        stored_original_query = response_data.get('task', {}).get('original_query', '')
        if stored_original_query == original_query:
            task_responses[key] = response_data

    if not task_responses:
        print("No task responses found for synthesis", flush=True)
        return

    # Count unique agents that contributed
    unique_agents = set()
    for response_data in task_responses.values():
        agent_name = response_data.get("from_agent", "")
        if agent_name:
            unique_agents.add(agent_name)

    num_agents = len(unique_agents)
    print(f"[DEBUG] Synthesis: {len(task_responses)} responses from {num_agents} unique agents: {list(unique_agents)}")

    # Get user topic from first response
    first_response = next(iter(task_responses.values()))
    user_topic = first_response.get("user_topic", "user_session:main")

    print(f"Sending synthesis to user topic: {user_topic}", flush=True)

    # Send combined completion and synthesis status
    self.send_message(user_topic, f"🎯 All agents completed! 🧠 Synthesizing {num_agents} agent responses into final answer...")

    # Create a synthesis prompt
    synthesis_prompt = f"""
    Synthesize these agent responses into a concise, well-structured answer:

    Original Task: {original_query}

    Agent Contributions:
    """

    for response_key, response_data in task_responses.items():
        # Extract the full response content for synthesis
        result = response_data['result']
        synthesis_prompt += f"\n{response_data['from_agent'].title()}: {result}\n"

    synthesis_prompt += "\nCreate a comprehensive, well-structured final response that combines all agent contributions. Include detailed analysis, key insights, and actionable recommendations. Use proper markdown formatting with headers, lists, and emphasis where appropriate."

    # Get synthesis from AI
    synthesis_response = self.get_completion(
        messages=[{"role": "user", "content": synthesis_prompt}],
        system_prompt="You are an expert synthesis specialist who creates comprehensive, detailed responses from multiple agent contributions. You excel at combining diverse perspectives into cohesive, well-structured analyses with clear insights and actionable recommendations."
    )

    # Send the synthesized response back to user
    if synthesis_response:
        # Format with line breaks for readability
        formatted_response = synthesis_response.replace('. ', '.\n')
        self.send_message(user_topic, formatted_response)

        # Send completion summary
        self.send_message(user_topic, f"🎉 **Complete!** {num_agents} agents collaborated successfully.")
    else:
        self.send_message(user_topic, "I received responses from multiple agents but couldn't synthesize them properly.")

    # Clean up pending responses for this task
    self.pending_responses = {k: v for k, v in self.pending_responses.items()
                            if v.get('task', {}).get('original_query', '') != original_query}


def _check_collaboration_completion(self, from_agent: str, task_result: str, original_task: dict, user_topic: str):
    """
    Check if incoming agent response completes any active collaborations.

    Monitors active collaborations and determines if all expected agents have
    responded. When complete, sends results to the user and triggers synthesis
    if multiple agents were involved.

    Args:
        self: The agent instance
        from_agent: Name of the agent sending the response
        task_result: The agent's response content
        original_task: The original task details
        user_topic: Topic to send responses back to
    """
    if not hasattr(self, 'active_collaborations'):
        return

    task_description = original_task.get('task', '')
    collaboration_key = f"collaboration_{task_description}_{user_topic}"

    if collaboration_key in self.active_collaborations:
        collaboration = self.active_collaborations[collaboration_key]

        # Add this response to the collaboration
        collaboration['received_responses'].append({
            'from_agent': from_agent,
            'result': task_result,
            'task': original_task
        })

        # Check if we have all expected responses
        expected_agents = set(collaboration['expected_agents'])
        received_agents = set(resp['from_agent'] for resp in collaboration['received_responses'])

        if expected_agents.issubset(received_agents):
            # All responses received - complete the collaboration

            # Send the actual response content to the user
            for response in collaboration['received_responses']:
                agent_name = response['from_agent']
                message_content = response['result']
                self.send_message(user_topic, f"**{agent_name.title()}:**\n\n{message_content}")

            self.send_message(user_topic, f"✅ Received responses from: {', '.join(received_agents)}")
            self.send_message(user_topic, "📋 Collaboration complete!")

            # Clean up the collaboration
            del self.active_collaborations[collaboration_key]

            # Trigger synthesis if needed
            if len(collaboration['received_responses']) > 1:
                _synthesize_collaboration_responses(self, collaboration)
        else:
            # Still waiting for more responses
            remaining = expected_agents - received_agents
            self.send_message(user_topic, f"⏳ Still waiting for: {', '.join(remaining)}")


def _synthesize_collaboration_responses(self, collaboration: dict):
    """
    Synthesize multiple agent responses from a collaboration.

    Creates a coherent final answer from multiple agent contributions using
    AI synthesis, specifically for explicit collaboration scenarios.

    Args:
        self: The agent instance
        collaboration: Dictionary containing:
            - task: The collaboration task
            - user_topic: Topic to send response to
            - received_responses: List of agent responses
    """
    user_topic = collaboration['user_topic']
    responses = collaboration['received_responses']

    if len(responses) <= 1:
        return

    self.send_message(user_topic, f"🧠 Synthesizing {len(responses)} agent responses...")

    # Create synthesis prompt
    synthesis_prompt = f"""
    Synthesize these agent responses into a coherent answer:

    Task: {collaboration['task']}

    Agent Responses:
    """

    for response in responses:
        synthesis_prompt += f"\n{response['from_agent'].title()}: {response['result']}\n"

    synthesis_prompt += "\nProvide a comprehensive, well-structured response combining all agent contributions."

    # Get synthesis from AI
    synthesis_response = self.get_completion(
        messages=[{"role": "user", "content": synthesis_prompt}],
        system_prompt="You are an expert at synthesizing multiple perspectives into coherent, comprehensive responses."
    )

    if synthesis_response:
        self.send_message(user_topic, f"🎯 **Final Answer:**\n\n{synthesis_response}")


def _cleanup_timed_out_collaborations(self):
    """
    Clean up collaborations that have timed out.

    Monitors active collaborations for timeouts and processes any responses
    that were received before the timeout. Sends appropriate messages to users
    about the timeout status.

    Args:
        self: The agent instance
    """
    if not hasattr(self, 'active_collaborations'):
        return

    current_time = time.time()
    timed_out_keys = []

    for key, collaboration in self.active_collaborations.items():
        if current_time - collaboration['start_time'] > collaboration['timeout']:
            timed_out_keys.append(key)
            user_topic = collaboration['user_topic']
            received_count = len(collaboration['received_responses'])

            if received_count > 0:
                self.send_message(user_topic, f"⏰ Collaboration timed out! Processing {received_count} received response{'s' if received_count > 1 else ''}...")
                if received_count > 1:
                    _synthesize_collaboration_responses(self, collaboration)
                else:
                    # Single response - just show it
                    response = collaboration['received_responses'][0]
                    self.send_message(user_topic, f"📋 **Response from {response['from_agent'].title()}:**\n\n{response['result']}")
            else:
                self.send_message(user_topic, "⏰ Collaboration timed out with no responses received.")

    # Remove timed-out collaborations
    for key in timed_out_keys:
        del self.active_collaborations[key]
