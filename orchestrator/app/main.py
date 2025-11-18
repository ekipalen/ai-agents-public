import nest_asyncio
nest_asyncio.apply()

# orchestrator/app/main.py - Refactored with modular architecture
import asyncio
import signal
from fastapi import FastAPI, Depends, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List
import time
import redis
import os
from pathlib import Path
import json
import requests

# Load environment variables from .env file
def load_env_file():
    """Load environment variables from .env file in project root."""
    env_path = Path("../.env")
    if env_path.exists():
        print(f"Loading environment variables from .env file: {env_path.absolute()}")
        loaded_vars = []
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key] = value
                        loaded_vars.append(f"{key}={value[:30]}...")
        print(f"✅ Environment variables loaded: {len(loaded_vars)} vars")
    else:
        print(f"⚠️  No .env file found at: {env_path.absolute()}")

# Load environment variables on startup
load_env_file()

from sqlalchemy.orm import Session
from . import models
from .database import SessionLocal, engine
from .action_client import ActionServerClient, Action

# Import from new modules
from . import agent_lifecycle
from . import routing
from . import action_management
from . import runbook_manager

models.Base.metadata.create_all(bind=engine)

# Simplified startup - immediate shutdown on Ctrl+C
app = FastAPI(title="Orchestrator")

# Configure logging to reduce uvicorn verbosity
import logging
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)

# Add CORS middleware to allow requests from the frontend
# Development: Allow all origins for easier debugging across different hostnames/IPs
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

# In-memory storage for chat histories
# Structure: {session_id: {agent_name: [messages]}}
chat_histories: Dict[str, Dict[str, List[Dict[str, str]]]] = {}

# In-memory storage for agent runbooks
agent_runbooks: Dict[str, Dict[str, Any]] = {}

# In-memory storage for action servers configuration
action_servers: Dict[str, Dict[str, Any]] = {}

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=0
)

# Request/Response Models
class AgentRegistration(BaseModel):
    id: str
    name: str
    role: str | None = None
    inbox_topic: str
    status_endpoint: str | None = None

class AgentInfo(AgentRegistration):
    last_seen_at: float
    status: str
    pid: int | None = None

class StartRequest(BaseModel):
    name: str

class InvokePayload(BaseModel):
    message: str

class CreateAgentRequest(BaseModel):
    name: str
    role: str
    capabilities: List[Dict[str, Any]]
    action_server: str = None

class DeleteAgentRequest(BaseModel):
    name: str
    remove_runbook: bool = False

class AssignActionServerRequest(BaseModel):
    agent_name: str
    action_server: str

class RemoveActionServerRequest(BaseModel):
    agent_name: str

class ShutdownRequest(BaseModel):
    force: bool = False

def signal_handler(signum, frame):
    """Handle shutdown signals - force immediate exit."""
    print(f"\n🛑 Received signal {signum} - force exiting immediately...")
    os._exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Track orchestrator startup time for frontend to detect restarts
ORCHESTRATOR_STARTUP_TIME = time.time()

async def start_agents_after_server_ready():
    """Start agents after the server is ready to accept connections."""
    # Wait for server to be fully ready
    print("⏳ Waiting 2 seconds for server to be fully ready...")
    await asyncio.sleep(2)

    # Load agent action configurations FIRST (before starting agents)
    print("🔍 Discovering actions from action servers...")
    action_management.load_agent_action_configs(action_servers)

    # Auto-start all agents
    print("🚀 Auto-starting all agents...")
    started_count = 0
    failed_count = 0

    for agent_name in agent_runbooks.keys():
        try:
            print(f"  Starting {agent_name}...")
            result = agent_lifecycle.start_agent_by_name(agent_name)
            if result.get("ok"):
                print(f"  ✅ {agent_name} started")
                started_count += 1
            else:
                print(f"  ⚠️  Failed to start {agent_name}: {result.get('error')}")
                failed_count += 1
        except Exception as e:
            print(f"  ⚠️  Error starting {agent_name}: {e}")
            failed_count += 1

    print(f"✅ Auto-start complete: {started_count} started, {failed_count} failed")

@app.on_event("startup")
async def startup_event():
    try:
        redis_client.ping()
        print("Connected to Redis successfully.")
    except redis.exceptions.ConnectionError as e:
        print(f"Failed to connect to Redis on startup: {e}")

    # Clean up stale agent records from previous runs
    db = SessionLocal()
    try:
        agent_lifecycle.cleanup_stale_agents(db)
    finally:
        db.close()

    # Load all agent runbooks from filesystem
    global agent_runbooks
    agent_runbooks = runbook_manager.load_runbooks_from_filesystem()

    # Load action servers configuration
    global action_servers
    action_servers = action_management.load_action_servers_config()

    # Start agents in background after server is ready
    asyncio.create_task(start_agents_after_server_ready())

# Health and Status Endpoints
@app.get("/health")
def health():
    return {"status": "ok", "ts": time.time()}

@app.get("/startup_time")
def get_startup_time():
    """Return orchestrator startup time for frontend to detect restarts."""
    return {"startup_time": ORCHESTRATOR_STARTUP_TIME}

@app.post("/shutdown")
def shutdown(request: ShutdownRequest = ShutdownRequest()):
    """Shutdown the orchestrator and all running agents."""
    shutdown_type = "FORCE" if request.force else "GRACEFUL"
    print(f"🛑 {shutdown_type} shutdown requested...")

    killed_count = 0
    for agent_name, proc_info in list(agent_lifecycle.running_processes.items()):
        try:
            process = proc_info["process"]
            if request.force:
                process.kill()
            else:
                process.terminate()

            try:
                if "log_file" in proc_info and proc_info["log_file"]:
                    proc_info["log_file"].close()
            except Exception:
                pass

            print(f"  ✓ Stopped agent: {agent_name}")
            killed_count += 1
        except Exception as e:
            print(f"  ✗ Error stopping agent {agent_name}: {e}")

    print(f"🛑 Stopped {killed_count} agents, exiting...")
    os._exit(0)
    return {"message": "Shutdown complete"}

# Agent Management Endpoints
@app.get("/agents", response_model=List[AgentInfo])
def list_agents(db: Session = Depends(get_db)):
    agents = db.query(models.Agent).all()
    return agents

@app.get("/agents/available")
def available_agents():
    """Scans the filesystem for available agents."""
    agents_dir = Path("../agents")
    runbooks_dir = Path("../runbooks")
    available = []

    if agents_dir.exists() and agents_dir.is_dir():
        for entry in agents_dir.iterdir():
            if entry.is_dir() and (entry / "main.py").exists():
                available.append(entry.name)

    if runbooks_dir.exists() and runbooks_dir.is_dir():
        for runbook_file in runbooks_dir.glob("*.md"):
            agent_name = runbook_file.stem
            if agent_name not in available:
                available.append(agent_name)

    return sorted(available)

@app.post("/agents/register", response_model=AgentInfo)
def register_agent(agent: AgentRegistration, db: Session = Depends(get_db)):
    db_agent = db.query(models.Agent).filter(models.Agent.name == agent.name).first()

    current_time = time.time()
    proc_info = agent_lifecycle.running_processes.get(agent.name)
    pid = proc_info["process"].pid if proc_info else None

    if db_agent:
        db_agent.id = agent.id
        db_agent.role = agent.role
        db_agent.inbox_topic = agent.inbox_topic
        db_agent.status_endpoint = agent.status_endpoint
        db_agent.last_seen_at = current_time
        db_agent.status = "running"
        db_agent.pid = pid
    else:
        db_agent = models.Agent(
            **agent.model_dump(),
            last_seen_at=current_time,
            status="running",
            pid=pid
        )
        db.add(db_agent)

    db.commit()
    db.refresh(db_agent)

    # If assistant just registered, notify the frontend
    if agent.name == "assistant":
        try:
            redis_client.publish("user_session:main", "[ASSISTANT_READY]")
            print(f"📢 Notified frontend that assistant is ready for session 'main'")
        except Exception as e:
            print(f"⚠️  Failed to notify frontend about assistant readiness: {e}")

    return db_agent

@app.post("/agents/start")
def start_agent(req: StartRequest, db: Session = Depends(get_db)):
    """API endpoint to start an agent."""
    return agent_lifecycle.start_agent_by_name(req.name)

@app.post("/agents/{agent_id}/stop")
def stop_agent(agent_id: str, db: Session = Depends(get_db)):
    """Stop an agent by ID."""
    db_agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()
    if not db_agent:
        return {"ok": False, "error": "Agent not found"}

    return agent_lifecycle.stop_agent_process(db_agent.name, db)

@app.post("/agents/stop")
def stop_agent_by_name(req: StartRequest, db: Session = Depends(get_db)):
    """Stop an agent by name."""
    return agent_lifecycle.stop_agent_process(req.name, db)

@app.post("/agents/create")
def create_agent(req: CreateAgentRequest, db: Session = Depends(get_db)):
    """Create a new agent with runbook and start it."""
    agent_name = req.name.lower().replace(" ", "_")

    # Validate agent name
    if not agent_name.replace("_", "").isalnum():
        return {"ok": False, "error": "Agent name must contain only letters, numbers, and underscores"}

    # Check if agent already exists
    existing_agent = db.query(models.Agent).filter(models.Agent.name == agent_name).first()
    if existing_agent:
        return {"ok": False, "error": f"Agent '{agent_name}' already exists"}

    # Check if runbook already exists
    runbooks_dir = Path("../runbooks")
    runbook_file = runbooks_dir / f"{agent_name}.md"
    if runbook_file.exists():
        runbook_file.unlink()
        print(f"🧹 Cleaned up orphaned runbook for agent: {agent_name}")

    try:
        # Generate runbook content
        runbook_content = agent_lifecycle.generate_agent_runbook(agent_name, req.role, req.capabilities)

        # Write runbook file
        runbooks_dir.mkdir(exist_ok=True)
        with open(runbook_file, "w", encoding="utf-8") as f:
            f.write(runbook_content)

        print(f"📝 Created runbook for agent: {agent_name}")

        # Register runbook in memory
        runbook_data = agent_lifecycle.parse_runbook_content(runbook_content)
        agent_runbooks[agent_name] = runbook_data

        # If action_server specified, create agent config file
        if req.action_server:
            config_dir = Path("../agent_configs")
            config_dir.mkdir(exist_ok=True)
            config_file = config_dir / f"{agent_name}.json"

            config_data = {
                "agent_name": agent_name,
                "action_server": req.action_server
            }

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2)

            print(f"📝 Created action config for agent: {agent_name} -> {req.action_server}")

        # If agent has action_server, discover actions BEFORE starting
        if req.action_server:
            try:
                print(f"🔍 Discovering actions for {agent_name} before starting...")
                action_management.load_agent_action_configs(action_servers)
                print(f"✅ Actions discovered and saved to DB for {agent_name}")
            except Exception as e:
                print(f"⚠️  Failed to discover actions for {agent_name}: {e}")

        # Start the agent
        start_result = agent_lifecycle.start_agent_by_name(agent_name)

        if start_result["ok"]:
            return {
                "ok": True,
                "message": f"Agent '{agent_name}' created and started successfully",
                "agent_name": agent_name,
                "runbook_created": True,
                "action_server_assigned": req.action_server is not None
            }
        else:
            # Clean up files if start failed
            if runbook_file.exists():
                runbook_file.unlink()
            if req.action_server:
                config_file = Path("../agent_configs") / f"{agent_name}.json"
                if config_file.exists():
                    config_file.unlink()
            return {"ok": False, "error": f"Agent created but failed to start: {start_result.get('error', 'Unknown error')}"}

    except Exception as e:
        # Clean up on failure
        if runbook_file.exists():
            runbook_file.unlink()
        if req.action_server:
            config_file = Path("../agent_configs") / f"{agent_name}.json"
            if config_file.exists():
                config_file.unlink()
        return {"ok": False, "error": f"Failed to create agent: {str(e)}"}

@app.post("/agents/delete")
def delete_agent(req: DeleteAgentRequest, db: Session = Depends(get_db)):
    """Delete an agent by stopping it and optionally removing its runbook."""
    agent_name = req.name

    if agent_name == "assistant":
        return {"ok": False, "error": "Cannot delete the assistant agent"}

    db_agent = db.query(models.Agent).filter(models.Agent.name == agent_name).first()
    if not db_agent:
        runbooks_dir = Path("../runbooks")
        runbook_file = runbooks_dir / f"{agent_name}.md"
        if not runbook_file.exists():
            return {"ok": False, "error": f"Agent '{agent_name}' not found"}

    try:
        stop_success = False

        if agent_name in agent_lifecycle.running_processes:
            stop_result = agent_lifecycle.stop_agent_process(agent_name, db)
            if stop_result["ok"]:
                stop_success = True
            else:
                print(f"Warning: Normal stop failed for {agent_name}: {stop_result.get('error')}")

        if not stop_success and db_agent and db_agent.status == "running" and db_agent.pid:
            try:
                print(f"Trying to kill agent {agent_name} by PID {db_agent.pid}")
                os.kill(db_agent.pid, 15)
                time.sleep(2)

                try:
                    os.kill(db_agent.pid, 0)
                    os.kill(db_agent.pid, 9)
                    time.sleep(1)
                    print(f"Force killed agent {agent_name}")
                except ProcessLookupError:
                    print(f"Agent {agent_name} stopped by PID kill")

                stop_success = True
            except Exception as e:
                print(f"PID kill failed for agent {agent_name}: {e}")

        if db_agent:
            db.delete(db_agent)
            db.commit()
            print(f"🗑️ Deleted agent '{agent_name}' from database")

        agent_lifecycle.running_processes.pop(agent_name, None)

        runbooks_dir = Path("../runbooks")
        runbook_file = runbooks_dir / f"{agent_name}.md"
        runbook_removed = False

        if req.remove_runbook and runbook_file.exists():
            runbook_file.unlink()
            runbook_removed = True
            print(f"🗑️ Removed runbook for agent: {agent_name}")

        # Always clean up agent config file (action server assignment)
        config_file = Path("../agent_configs") / f"{agent_name}.json"
        config_removed = False
        if config_file.exists():
            config_file.unlink()
            config_removed = True
            print(f"🗑️ Removed config file for agent: {agent_name}")

        agent_runbooks.pop(agent_name, None)

        return {
            "ok": True,
            "message": f"Agent '{agent_name}' deleted successfully",
            "runbook_removed": runbook_removed,
            "config_removed": config_removed,
            "process_stopped": stop_success
        }

    except Exception as e:
        error_msg = f"Failed to delete agent '{agent_name}': {str(e)}"
        print(f"ERROR in delete_agent: {error_msg}")
        return {"ok": False, "error": error_msg}

# Action Server Management Endpoints
@app.get("/action-servers/available")
def get_available_action_servers():
    """Get list of available action servers."""
    try:
        config_file = Path("../action_servers.json")
        if not config_file.exists():
            return {"servers": []}

        with open(config_file, 'r') as f:
            config = json.load(f)

        servers = []
        for server_id, server_data in config.get("servers", {}).items():
            servers.append({
                "id": server_id,
                "name": server_data.get("name"),
                "description": server_data.get("description"),
                "type": server_data.get("type"),
                "url": server_data.get("url")
            })

        return {"servers": servers}

    except Exception as e:
        return {"ok": False, "error": f"Failed to load action servers: {str(e)}"}

@app.post("/agents/assign-action-server")
def assign_action_server(req: AssignActionServerRequest, db: Session = Depends(get_db)):
    """Assign an action server to an agent."""
    try:
        agent = db.query(models.Agent).filter(models.Agent.name == req.agent_name).first()
        if not agent:
            return {"ok": False, "error": f"Agent '{req.agent_name}' not found"}

        config_file = Path("../action_servers.json")
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
                if req.action_server not in config.get("servers", {}):
                    return {"ok": False, "error": f"Action server '{req.action_server}' not found"}

        config_dir = Path("../agent_configs")
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / f"{req.agent_name}.json"

        config_data = {
            "agent_name": req.agent_name,
            "action_server": req.action_server
        }

        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)

        print(f"📝 Assigned action server '{req.action_server}' to agent '{req.agent_name}'")

        action_management.load_agent_action_configs(action_servers)

        agent_restarted = False
        if agent.status == "running":
            print(f"🔄 Restarting agent '{req.agent_name}' to load new actions...")
            try:
                stop_result = agent_lifecycle.stop_agent_process(req.agent_name, db)
                if stop_result.get("ok"):
                    time.sleep(1)
                    start_result = agent_lifecycle.start_agent_by_name(req.agent_name)
                    if start_result.get("ok"):
                        agent_restarted = True
                        print(f"✅ Agent '{req.agent_name}' restarted successfully")
                    else:
                        print(f"⚠️ Failed to restart agent: {start_result.get('error')}")
                else:
                    print(f"⚠️ Failed to stop agent for restart: {stop_result.get('error')}")
            except Exception as e:
                print(f"⚠️ Error restarting agent: {e}")

        return {
            "ok": True,
            "message": f"Action server '{req.action_server}' assigned to agent '{req.agent_name}'",
            "agent_restarted": agent_restarted,
            "note": "Agent restarted and tools are now available" if agent_restarted else "Agent will load tools on next start"
        }

    except Exception as e:
        return {"ok": False, "error": f"Failed to assign action server: {str(e)}"}

@app.post("/agents/remove-action-server")
def remove_action_server(req: RemoveActionServerRequest, db: Session = Depends(get_db)):
    """Remove action server from an agent."""
    try:
        agent = db.query(models.Agent).filter(models.Agent.name == req.agent_name).first()
        if not agent:
            return {"ok": False, "error": f"Agent '{req.agent_name}' not found"}

        config_file = Path("../agent_configs") / f"{req.agent_name}.json"
        if not config_file.exists():
            return {"ok": False, "error": f"Agent '{req.agent_name}' has no action server assigned"}

        config_file.unlink()
        print(f"🗑️ Removed action server from agent '{req.agent_name}'")

        agent.actions = None
        db.commit()
        print(f"🧹 Cleared actions from database for agent '{req.agent_name}'")

        return {
            "ok": True,
            "message": f"Action server removed from agent '{req.agent_name}'",
            "note": "Agent will no longer have access to MCP tools"
        }

    except Exception as e:
        return {"ok": False, "error": f"Failed to remove action server: {str(e)}"}

@app.post("/agents/{agent_id}/invoke")
def invoke_agent(agent_id: str, payload: InvokePayload, db: Session = Depends(get_db)):
    db_agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()
    if not db_agent:
        return {"ok": False, "error": "Agent not found"}

    try:
        messages = [{"role": "user", "content": payload.message}]
        payload_to_send = {
            "messages": messages,
            "reply_to": "user_session:main"
        }
        message = json.dumps(payload_to_send)
        redis_client.publish(db_agent.inbox_topic, message)
        return {"ok": True, "message": f"Message sent to {db_agent.name}"}
    except redis.exceptions.RedisError as e:
        return {"ok": False, "error": str(e)}

# Runbook Management Endpoints
@app.post("/agents/runbooks")
def register_runbook(runbook: Dict[str, Any]):
    """Register an agent runbook."""
    agent_name = runbook.get("agent_name")
    if not agent_name:
        return {"ok": False, "error": "agent_name is required"}

    agent_runbooks[agent_name] = runbook
    print(f"Registered runbook for agent: {agent_name}")
    return {"ok": True, "message": f"Runbook registered for {agent_name}"}

@app.get("/agents/runbooks")
def get_all_runbooks():
    """Get all registered agent runbooks."""
    return list(agent_runbooks.values())

@app.post("/chat/{session_id}/clear")
def clear_chat_history(session_id: str):
    """Clear chat history for a specific session (all agents)."""
    if session_id in chat_histories:
        total_messages = sum(len(messages) for messages in chat_histories[session_id].values())
        chat_histories[session_id] = {}
        return {"message": f"Cleared {total_messages} messages for session {session_id}"}
    else:
        return {"message": f"No chat history found for session {session_id}"}

@app.get("/chat/{session_id}/history")
def get_chat_history(session_id: str):
    """Get chat history for a specific session (per-agent breakdown)."""
    if session_id in chat_histories:
        total_messages = sum(len(messages) for messages in chat_histories[session_id].values())
        return {
            "session_id": session_id,
            "message_count": total_messages,
            "agents": chat_histories[session_id]
        }
    else:
        return {"session_id": session_id, "message_count": 0, "agents": {}}

@app.get("/agents/runbooks/{agent_name}")
def get_agent_runbook(agent_name: str):
    """Get a specific agent's runbook."""
    if agent_name not in agent_runbooks:
        return {"error": f"Runbook not found for agent {agent_name}"}
    return agent_runbooks[agent_name]

@app.get("/agents/capabilities")
def get_all_capabilities():
    """Get all agent capabilities across all runbooks."""
    capabilities = []
    for runbook in agent_runbooks.values():
        for capability in runbook.get("capabilities", []):
            capabilities.append({
                "agent": runbook["agent_name"],
                "capability": capability
            })
    return capabilities

# Action Management Endpoints
class ExecuteActionRequest(BaseModel):
    action_id: str
    parameters: Dict[str, Any]

@app.get("/agents/{agent_name}/actions")
def get_agent_actions(agent_name: str, db: Session = Depends(get_db)):
    """Get all actions for a specific agent."""
    agent = db.query(models.Agent).filter(models.Agent.name == agent_name).first()
    if not agent:
        return {"error": f"Agent '{agent_name}' not found"}

    action_server_info = None
    if agent.action_server_name and agent.action_server_name in action_servers:
        server = action_servers[agent.action_server_name]
        action_server_info = {
            "name": server.get("name"),
            "type": server.get("type"),
            "url": server.get("url")
        }

    return {
        "agent_name": agent_name,
        "action_server": action_server_info,
        "actions": agent.actions or []
    }

@app.post("/agents/{agent_name}/actions/execute")
def execute_agent_action(
    agent_name: str,
    request: ExecuteActionRequest,
    db: Session = Depends(get_db)
):
    """Execute an action for a specific agent."""
    agent = db.query(models.Agent).filter(models.Agent.name == agent_name).first()
    if not agent:
        return {"error": f"Agent '{agent_name}' not found"}

    if not agent.action_server_name:
        return {"error": f"Agent '{agent_name}' does not have an action server configured"}

    if agent.action_server_name not in action_servers:
        return {"error": f"Action server '{agent.action_server_name}' not found in configuration"}

    server_config = action_servers[agent.action_server_name]

    actions = agent.actions or []
    action = None
    for a in actions:
        if a.get("id") == request.action_id:
            action = a
            break

    if not action:
        return {"error": f"Action '{request.action_id}' not found for agent '{agent_name}'"}

    if not action.get("enabled", True):
        return {"error": f"Action '{request.action_id}' is disabled"}

    try:
        client = ActionServerClient(
            base_url=server_config["url"],
            bearer_token=server_config.get("token")
        )

        result = client.execute_action(action["endpoint"], request.parameters)
        return {
            "agent_name": agent_name,
            "action_id": request.action_id,
            "action_name": action.get("name"),
            "result": result.get("result"),
            "error": result.get("error")
        }

    except Exception as e:
        return {"error": f"Failed to execute action: {str(e)}"}

@app.get("/actions/all")
def get_all_actions(db: Session = Depends(get_db)):
    """Get all actions across all agents."""
    all_actions = []
    agents = db.query(models.Agent).all()

    for agent in agents:
        if agent.actions:
            for action in agent.actions:
                all_actions.append({
                    "agent_name": agent.name,
                    "agent_role": agent.role,
                    "action": action
                })

    return {
        "total_agents": len(agents),
        "total_actions": len(all_actions),
        "actions": all_actions
    }

@app.get("/actions/search")
def search_actions(query: str, db: Session = Depends(get_db)):
    """Search for actions by query string."""
    query_lower = query.lower()
    matching_actions = []
    agents = db.query(models.Agent).all()

    for agent in agents:
        if agent.actions:
            for action in agent.actions:
                action_name = action.get("name", "").lower()
                action_desc = action.get("description", "").lower()
                agent_name = agent.name.lower()

                if (query_lower in action_name or
                    query_lower in action_desc or
                    query_lower in agent_name):
                    matching_actions.append({
                        "agent_name": agent.name,
                        "agent_role": agent.role,
                        "action": action,
                        "relevance": "high" if query_lower in action_name else "medium"
                    })

    matching_actions.sort(key=lambda x: x["relevance"], reverse=True)

    return {
        "query": query,
        "total_matches": len(matching_actions),
        "matches": matching_actions
    }

@app.post("/actions/reload")
def reload_action_configs():
    """Manually reload action configurations for all agents."""
    try:
        action_management.load_agent_action_configs(action_servers)
        return {"ok": True, "message": "Action configurations reloaded"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.post("/actions/discover/{server_name}")
def discover_actions_from_server(server_name: str):
    """Manually discover actions from an MCP server."""
    if server_name not in action_servers:
        return {"error": f"Action server '{server_name}' not found"}

    server_config = action_servers[server_name]

    try:
        client = ActionServerClient(
            base_url=server_config["url"],
            bearer_token=server_config.get("token")
        )

        actions = client.list_actions()
        action_dicts = [action.to_dict() for action in actions]

        return {
            "server_name": server_name,
            "server_url": server_config["url"],
            "total_actions": len(action_dicts),
            "actions": action_dicts
        }

    except Exception as e:
        return {"error": f"Failed to discover actions: {str(e)}"}

@app.post("/agents/{agent_name}/actions/refresh")
def refresh_agent_actions(agent_name: str, db: Session = Depends(get_db)):
    """Refresh an agent's actions by re-discovering from its action server."""
    agent = db.query(models.Agent).filter(models.Agent.name == agent_name).first()
    if not agent:
        return {"error": f"Agent '{agent_name}' not found"}

    if not agent.action_server_name:
        return {"error": f"Agent '{agent_name}' has no action server configured"}

    if agent.action_server_name not in action_servers:
        return {"error": f"Action server '{agent.action_server_name}' not found"}

    server_config = action_servers[agent.action_server_name]

    if not server_config.get("auto_discover", False):
        return {"error": f"Action server '{agent.action_server_name}' does not have auto_discover enabled"}

    try:
        client = ActionServerClient(
            base_url=server_config["url"],
            bearer_token=server_config.get("token")
        )

        discovered_actions = client.list_actions()
        agent.actions = [action.to_dict() for action in discovered_actions]

        db.commit()

        return {
            "agent_name": agent_name,
            "server_name": agent.action_server_name,
            "total_actions": len(agent.actions),
            "actions": agent.actions
        }

    except Exception as e:
        db.rollback()
        return {"error": f"Failed to refresh actions: {str(e)}"}

# WebSocket Chat Endpoint
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for unified chat with @mention routing."""
    await websocket.accept()

    # Initialize per-agent conversation histories for this session
    if session_id not in chat_histories:
        chat_histories[session_id] = {}
        print(f"✅ WebSocket connection accepted for session '{session_id}' - new session.")
    else:
        print(f"✅ WebSocket connection accepted for session '{session_id}' - restored session with {len(chat_histories[session_id])} agent conversations.")

    agent_id = None
    db = SessionLocal()

    user_session_topic = f"user_session:{session_id}"

    async def redis_to_ws():
        print(f"  -> Starting redis_to_ws task for {session_id}")
        pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
        pubsub.subscribe(user_session_topic)
        print(f"  -> Subscribed to Redis topic: {user_session_topic}")

        try:
            while True:
                try:
                    message = pubsub.get_message(timeout=1.0)
                    if message and message['type'] == 'message':
                        print(f"  <- Received message from Redis on topic {message['channel'].decode()}: {message['data'][:100]}...")
                        message_data_str = message['data'].decode()

                        # Handle READY messages from any agent
                        if message_data_str == "[ASSISTANT_READY]":
                            print(f"  🤖 Assistant is ready, sending introduction for {session_id}")
                            await routing.send_assistant_introduction(websocket, session_id, agent_runbooks, agent_lifecycle.running_processes)
                            continue

                        try:
                            message_obj = json.loads(message_data_str)
                            content = message_obj.get("content", "")
                            agent_name = message_obj.get("sender", "assistant")

                            # Store in per-agent conversation history
                            if agent_name not in chat_histories[session_id]:
                                chat_histories[session_id][agent_name] = []
                            chat_histories[session_id][agent_name].append({"role": "assistant", "content": content})
                            print(f"  -> Appended {agent_name} message to history")

                            # Check if agent's response contains @mentions
                            mentioned_agents, cleaned_content = routing.extract_mentions(content)
                            if mentioned_agents:
                                print(f"  🤝 Agent {agent_name} mentioned {mentioned_agents}, routing to them...")

                                import re
                                lines = content.split('\n')
                                agent_messages = {}

                                for mentioned in mentioned_agents:
                                    agent_messages[mentioned] = []

                                for line in lines:
                                    line = line.strip()
                                    if not line:
                                        continue

                                    line_has_mention = False
                                    for agent in mentioned_agents:
                                        if f'@{agent}' in line.lower():
                                            line_has_mention = True
                                            cleaned_line = re.sub(rf'@{agent}\s*', '', line, flags=re.IGNORECASE).strip()
                                            agent_messages[agent].append(cleaned_line)

                                    if not line_has_mention:
                                        for mentioned in mentioned_agents:
                                            agent_messages[mentioned].append(line)

                                db_temp = SessionLocal()
                                try:
                                    for target_agent_name in mentioned_agents:
                                        target_agent = db_temp.query(models.Agent).filter(models.Agent.name == target_agent_name).first()

                                        if not target_agent:
                                            print(f"  ⚠️  Cannot route to {target_agent_name} (agent not found)")
                                            continue

                                        if target_agent.status != "running":
                                            print(f"  ⚠️  Cannot route to {target_agent_name} (not running)")
                                            continue

                                        if target_agent_name not in chat_histories[session_id]:
                                            chat_histories[session_id][target_agent_name] = []

                                        agent_specific_content = '\n'.join(agent_messages.get(target_agent_name, [cleaned_content]))

                                        chat_histories[session_id][target_agent_name].append({"role": "user", "content": agent_specific_content})

                                        payload = {
                                            "messages": chat_histories[session_id][target_agent_name],
                                            "reply_to": user_session_topic,
                                            "agent": target_agent_name
                                        }
                                        redis_client.publish(target_agent.inbox_topic, json.dumps(payload))
                                        print(f"  ✅ Routed {agent_name}'s message to {target_agent_name}: '{agent_specific_content[:50]}...'")
                                finally:
                                    db_temp.close()

                            # Prefix response with agent name if not assistant
                            if agent_name != "assistant":
                                content_to_send = f"[{agent_name.title()}]: {content}"
                            else:
                                content_to_send = content

                            print(f"  -> Sending to WebSocket: {content_to_send[:100]}...")
                            await websocket.send_text(content_to_send)
                        except json.JSONDecodeError:
                            print(f"  ⚠️  Received non-JSON message on user topic, sending raw to frontend: {message_data_str}")
                            await websocket.send_text(message_data_str)

                    await asyncio.sleep(0.01)
                except Exception as e:
                    print(f"  💥 ERROR in redis_to_ws for {session_id}: {e}")
                    break
        finally:
            pubsub.unsubscribe()
            pubsub.close()
            print(f"  <- Exiting redis_to_ws loop for {session_id}")

    async def ws_to_redis():
        print(f"  -> Starting ws_to_redis task for {session_id}")

        try:
            while True:
                try:
                    prompt = await websocket.receive_text()
                    print(f"  -> Received prompt from WebSocket: '{prompt}'")

                    # Extract @mentions if present
                    mentioned_agents, cleaned_message = routing.extract_mentions(prompt)

                    # Smart routing logic
                    if mentioned_agents:
                        if mentioned_agents[0] == "assistant":
                            target_agent_names = ["assistant"]
                            import re
                            message_to_send = re.sub(r'@' + re.escape(mentioned_agents[0]) + r'\b\s*', '', prompt, count=1).strip()
                            print(f"  -> Delegation mode: routing to assistant only, preserving nested mentions")
                        else:
                            target_agent_names = mentioned_agents
                            message_to_send = cleaned_message
                            print(f"  -> Parallel broadcast mode: routing to all {len(mentioned_agents)} agents")
                    else:
                        target_agent_names = ["assistant"]
                        message_to_send = cleaned_message

                    print(f"  -> Routing to {len(target_agent_names)} agent(s): {target_agent_names} (message: '{message_to_send[:50]}...')")

                    successful_agents = []
                    failed_agents = []

                    db = SessionLocal()
                    try:
                        for target_agent_name in target_agent_names:
                            target_agent = db.query(models.Agent).filter(models.Agent.name == target_agent_name).first()

                            if not target_agent:
                                print(f"  ⚠️  WARNING: Agent '{target_agent_name}' not found in DB - skipping")
                                failed_agents.append(f"{target_agent_name} (not available)")
                                continue

                            if target_agent.status != "running":
                                print(f"  ⚠️  WARNING: Agent '{target_agent_name}' is not running (status: {target_agent.status}).")
                                failed_agents.append(f"{target_agent_name} (not running)")
                                continue

                            if target_agent_name not in chat_histories[session_id]:
                                chat_histories[session_id][target_agent_name] = []

                            chat_histories[session_id][target_agent_name].append({"role": "user", "content": message_to_send})

                            payload = {
                                "messages": chat_histories[session_id][target_agent_name],
                                "reply_to": user_session_topic,
                                "agent": target_agent_name
                            }
                            print(f"  -> Publishing to Redis topic '{target_agent.inbox_topic}' with {len(chat_histories[session_id][target_agent_name])} messages...")
                            redis_client.publish(target_agent.inbox_topic, json.dumps(payload))
                            successful_agents.append(target_agent_name)

                    finally:
                        db.close()

                    if failed_agents:
                        await websocket.send_text(f"⚠️  Some agents were unavailable: {', '.join(failed_agents)}")

                    if not successful_agents:
                        await websocket.send_text(f"⚠️  No agents were available to handle your message. Please check the dashboard.")

                except Exception as e:
                    print(f"  💥 ERROR in ws_to_redis for {session_id}: {e}")
                    break
        finally:
            print(f"  <- Exiting ws_to_redis loop for {session_id}")

    redis_task = asyncio.create_task(redis_to_ws())
    ws_task = asyncio.create_task(ws_to_redis())

    try:
        print(f"  -> Starting asyncio.gather for session {session_id}")
        await asyncio.gather(redis_task, ws_task, return_exceptions=True)

    except Exception as e:
        print(f"💥 WebSocket Error in gather for {session_id}: {e}")
    finally:
        print(f"❌ WebSocket connection closed for session {session_id}.")
