"""Constants for agent communication and message types."""

# Message Types
MSG_TYPE_NATURAL_CONVERSATION = "natural_conversation"
MSG_TYPE_NATURAL_CONVERSATION_RESPONSE = "natural_conversation_response"
MSG_TYPE_TASK_DELEGATION = "task_delegation"
MSG_TYPE_TASK_RESPONSE = "task_response"

# Contexts
CONTEXT_ASSISTANT_COORDINATION = "assistant_coordination"
CONTEXT_PEER_COLLABORATION = "peer_collaboration"

# Topic Prefixes
TOPIC_AGENT_INBOX = "agent:{}:inbox"
TOPIC_USER_SESSION = "user_session:{}"

# Agent Status
STATUS_RUNNING = "running"
STATUS_STOPPED = "stopped"
STATUS_FAILED = "failed"

# Priorities
PRIORITY_LOW = "low"
PRIORITY_NORMAL = "normal"
PRIORITY_HIGH = "high"
PRIORITY_URGENT = "urgent"

# Model Configuration
DEFAULT_MODEL = "gpt-5-nano"
DEFAULT_TEMPERATURE = 0.7
