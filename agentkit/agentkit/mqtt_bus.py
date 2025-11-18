# agents/common/mqtt_bus.py
import json
import threading
import time
from typing import Callable, Optional
import paho.mqtt.client as mqtt

OnMessage = Callable[[str, dict], None]  # (topic, payload_dict)

class MqttBus:
    def __init__(self, host: str, port: int = 1883, username: str = "", password: str = "", client_id: Optional[str] = None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311, clean_session=True)
        if username:
            self.client.username_pw_set(username, password)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self._on_message_cb: Optional[OnMessage] = None
        self._connected = threading.Event()

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        # reason_code == 0 means success
        self._connected.set()

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except Exception:
            payload = {"raw": msg.payload.decode("utf-8", errors="ignore")}
        if self._on_message_cb:
            self._on_message_cb(msg.topic, payload)

    def connect(self):
        self.client.connect(self.host, self.port, keepalive=30)
        self.client.loop_start()
        if not self._connected.wait(timeout=5):
            raise RuntimeError("MQTT connect timeout")

    def subscribe(self, topic: str, qos: int = 0):
        self.client.subscribe(topic, qos=qos)

    def publish_json(self, topic: str, data: dict, qos: int = 0, retain: bool = False):
        self.client.publish(topic, json.dumps(data), qos=qos, retain=retain)

    def set_on_message(self, cb: OnMessage):
        self._on_message_cb = cb

    def disconnect(self):
        try:
            self.client.loop_stop()
        finally:
            self.client.disconnect()