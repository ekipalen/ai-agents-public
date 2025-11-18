# orchestrator/app/models.py
from sqlalchemy import Column, String, Float, Integer, JSON, Text
from .database import Base

class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True, unique=True)
    role = Column(String, nullable=True)
    inbox_topic = Column(String)
    status_endpoint = Column(String, nullable=True)
    last_seen_at = Column(Float)
    status = Column(String, default="stopped")
    pid = Column(Integer, nullable=True)

    # Action server configuration
    action_server_name = Column(String, nullable=True)  # Reference to action server in config
    actions = Column(JSON, nullable=True, default=list)  # List of action dictionaries
