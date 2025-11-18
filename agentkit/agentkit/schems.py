# agents/common/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal
from uuid import uuid4
import time

MessageType = Literal["PING", "PONG", "TASK", "REPLY", "HEARTBEAT", "SUMMARIZE"]

class BusMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: MessageType
    source: str            # agent id of sender
    target: str            # agent id or "broadcast"
    created_at: float = Field(default_factory=lambda: time.time())
    corr_id: Optional[str] = None
    payload: Dict[str, Any] = {}

    def reply(self, source_id: str, payload: Dict[str, Any]):
        return BusMessage(
            type="REPLY",
            source=source_id,
            target=self.source,
            corr_id=self.corr_id or self.id,
            payload=payload,
        )

def inbox_topic_for(agent_id: str) -> str:
    return f"agents/{agent_id}/inbox"