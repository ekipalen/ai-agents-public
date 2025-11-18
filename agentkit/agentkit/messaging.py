"""Redis messaging functionality for agents."""
import json
import time
import redis
from threading import Thread
from typing import Callable, Dict, Any


class RedisMessenger:
    """Handles Redis pub/sub messaging for agents."""

    def __init__(self, redis_host: str, redis_port: int, agent_name: str):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.agent_name = agent_name
        self.redis_client = None

    def connect(self) -> bool:
        """Connect to Redis server."""
        try:
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=0
            )
            self.redis_client.ping()
            print(f"[{self.agent_name}] Connected to Redis successfully.", flush=True)
            return True
        except redis.exceptions.ConnectionError as e:
            print(f"[{self.agent_name}] Failed to connect to Redis: {e}", flush=True)
            return False

    def send_message(self, topic: str, message: str | Dict[str, Any]) -> bool:
        """
        Send a message to a Redis topic.

        Args:
            topic: Redis topic to publish to
            message: Message content (string or dict)

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.redis_client:
            print(f"[{self.agent_name}] Cannot send message, Redis client not connected.", flush=True)
            return False

        # Format message based on topic type
        if topic.startswith("user_session:"):
            # User-facing messages need structured format
            structured_message = {
                "sender": self.agent_name,
                "content": str(message),
                "timestamp": time.time()
            }
            message_str = json.dumps(structured_message)
        else:
            # Agent-to-agent messages
            if isinstance(message, dict):
                message_str = json.dumps(message)
            else:
                message_str = str(message)

        try:
            preview = message_str[:100] if message_str else "None"
            print(f"[{self.agent_name}] Sending to {topic}: {repr(preview)}", flush=True)

            self.redis_client.publish(topic, message_str)
            return True
        except redis.exceptions.RedisError as e:
            print(f"[{self.agent_name}] Failed to send message to {topic}: {e}", flush=True)
            return False

    def subscribe(self, topic: str, message_handler: Callable[[dict], None]):
        """
        Subscribe to a Redis topic in a background thread.

        Args:
            topic: Redis topic to subscribe to
            message_handler: Callback function to handle incoming messages
        """
        thread = Thread(
            target=self._subscribe_loop,
            args=(topic, message_handler),
            daemon=True
        )
        thread.start()
        print(f"[{self.agent_name}] Subscribed to {topic}", flush=True)

    def _subscribe_loop(self, topic: str, message_handler: Callable[[dict], None]):
        """Internal subscription loop running in background thread."""
        try:
            # Each thread needs its own Redis client
            redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=0
            )
            pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
            pubsub.subscribe(topic)

            for message in pubsub.listen():
                if message['type'] == 'message':
                    # Parse message data
                    raw_data = message['data'].decode()
                    try:
                        parsed_data = json.loads(raw_data)
                    except json.JSONDecodeError:
                        parsed_data = raw_data

                    # Add parsed data to message dict
                    message['parsed_data'] = parsed_data

                    # Call the handler
                    message_handler(message)

        except redis.exceptions.ConnectionError as e:
            print(f"[{self.agent_name}] Connection error in subscribe loop for {topic}: {e}", flush=True)
        except Exception as e:
            print(f"[{self.agent_name}] Unexpected error in subscribe loop for {topic}: {e}", flush=True)
