# agents/common/config.py
import os

def env_str(key: str, default: str = "") -> str:
    return os.getenv(key, default)

def env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, default))
    except ValueError:
        return default

class Settings:
    def __init__(self):
        self.AGENT_ID      = env_str("AGENT_ID", "agent-unknown")
        self.AGENT_NAME    = env_str("AGENT_NAME", self.AGENT_ID)
        self.AGENT_ROLE    = env_str("AGENT_ROLE", "")
        self.INBOX_TOPIC   = env_str("INBOX_TOPIC", f"agents/{self.AGENT_ID}/inbox")

        self.ORCH_URL      = env_str("ORCH_URL", "http://localhost:8000")
        self.MQTT_HOST     = env_str("MQTT_HOST", "localhost")
        self.MQTT_PORT     = env_int("MQTT_PORT", 1883)
        self.MQTT_USER     = env_str("MQTT_USER", "")
        self.MQTT_PASS     = env_str("MQTT_PASS", "")

        self.OPENAI_API_KEY = env_str("OPENAI_API_KEY", "")

        # Agent-specific knobs
        self.PING_TARGET_ROLE = env_str("PING_TARGET_ROLE", "ponger")
        self.PING_INTERVAL    = env_int("PING_INTERVAL", 5)