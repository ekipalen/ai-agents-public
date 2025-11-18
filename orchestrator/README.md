# Orchestrator - AI Agents Backend

The orchestrator is the central FastAPI backend that manages agent lifecycle, message routing, and MCP tool integration for the AI Agents system.

## Features

- **Agent Lifecycle Management** - Start, stop, create, and delete agents
- **Smart Message Routing** - Extract @mentions and route messages to appropriate agents
- **MCP Tool Integration** - Discover and execute tools via MCP servers
- **WebSocket Communication** - Real-time bidirectional chat
- **Redis Pub/Sub** - Agent-to-agent messaging
- **SQLite Database** - Agent state persistence

## Architecture

```
WebSocket ←→ Orchestrator ←→ Redis Pub/Sub ←→ Agents
                  ↓
            SQLite Database
                  ↓
            MCP Servers (Tools)
```

## Directory Structure

```
orchestrator/
├── app/
│   ├── main.py               # Main FastAPI app & WebSocket handler
│   ├── agent_lifecycle.py    # Agent start/stop/create/delete (348 lines)
│   ├── routing.py            # @mention extraction & routing (109 lines)
│   ├── action_management.py  # MCP tool configuration (165 lines)
│   ├── action_client.py      # MCP client implementation
│   └── runbook_manager.py    # Runbook loading (51 lines)
├── agents.db                 # SQLite database
└── .venv/                    # Virtual environment
```

## Installation

```bash
cd orchestrator
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e .
```

## Running

```bash
cd orchestrator
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 9000
```

The orchestrator will be available at `http://localhost:9000`

## API Endpoints

### WebSocket

- `WS /ws/{session_id}` - Real-time chat communication

### Agent Management

- `GET /agents` - List all agents
- `POST /agents/start` - Start an agent
  ```json
  {"name": "agent_name"}
  ```
- `POST /agents/stop` - Stop an agent
  ```json
  {"name": "agent_name"}
  ```
- `POST /agents/create` - Create new agent
  ```json
  {
    "name": "agent_name",
    "role": "Agent Role",
    "capabilities": [...]
  }
  ```
- `POST /agents/delete` - Delete agent
  ```json
  {
    "name": "agent_name",
    "remove_runbook": false
  }
  ```
- `GET /agents/runbooks` - Get all agent runbooks

### MCP Tools

- `GET /agents/{name}/actions` - Get agent's tools
- `POST /agents/{name}/actions/execute` - Execute a tool
  ```json
  {
    "action_id": "tool_id",
    "parameters": {...}
  }
  ```
- `GET /actions/all` - List all agent tools
- `GET /actions/search?query=...` - Search tools
- `GET /action-servers/available` - List configured MCP servers
- `POST /agents/assign-action-server` - Assign MCP server to agent
  ```json
  {
    "agent_name": "bob",
    "action_server": "email_mcp"
  }
  ```
- `POST /agents/remove-action-server` - Remove MCP server from agent
  ```json
  {"agent_name": "bob"}
  ```

## Configuration

### Environment Variables

Create `.env` in the project root:

```bash
OPENAI_API_KEY=your_key_here
ORCHESTRATOR_URL=http://localhost:9000
REDIS_HOST=localhost
REDIS_PORT=6379
```

### MCP Servers

Configure MCP servers in `action_servers.json`:

```json
{
  "servers": {
    "email_mcp": {
      "name": "email_mcp",
      "url": "https://your-mcp-server.example.com",
      "description": "Email tools (read, send, search)",
      "auto_discover": true
    }
  }
}
```

### Agent Tools

Configure agent-specific tools in `agent_configs/{agent_name}.json`:

```json
{
  "agent_name": "bob",
  "action_server": {
    "url": "https://your-mcp-server.example.com",
    "token": "your-bearer-token",
    "type": "mcp"
  },
  "actions": [...]
}
```

## Development

### Code Structure

The orchestrator is organized into focused modules after refactoring:

- **main.py** (1,102 lines) - Core FastAPI app, WebSocket, routing
- **agent_lifecycle.py** - All agent lifecycle operations
- **routing.py** - @mention parsing and validation
- **action_management.py** - MCP tool configuration loading
- **runbook_manager.py** - Runbook file loading

### Adding New Endpoints

1. Add route to `app/main.py`
2. Implement logic in appropriate module
3. Update this README with endpoint documentation

### Modifying Routing

Edit `app/routing.py`:
- `extract_mentions()` - Parse @mentions from messages
- `send_assistant_introduction()` - Customize agent introductions

### Testing

```bash
# Test WebSocket
wscat -c ws://localhost:9000/ws/test_session

# Test API endpoints
curl http://localhost:9000/agents
curl -X POST http://localhost:9000/agents/start -H "Content-Type: application/json" -d '{"name":"assistant"}'
```

## Troubleshooting

### Port Already in Use

```bash
# Find process using port 9000
lsof -i :9000

# Kill the process
kill -9 <PID>
```

### Database Issues

```bash
# Reset database (WARNING: Deletes all data)
rm agents.db
# Restart orchestrator to recreate
```

### Redis Connection Issues

```bash
# Check Redis is running
redis-cli ping
# Should return: PONG

# Start Redis if not running
redis-server
```

### Agent Won't Start

- Check agent directory exists: `agents/{agent_name}/`
- Verify `runbooks/{agent_name}.md` exists
- Check orchestrator logs for errors
- Ensure virtual environment is activated

## Logging

The orchestrator uses Python's logging module with colored output:

- **INFO** - General operations (startup, agent lifecycle)
- **WARNING** - Non-critical issues (agent already running)
- **ERROR** - Critical errors (agent start failures)

View logs in terminal where orchestrator is running.

## Performance

- **WebSocket connections**: Unlimited (limited by system resources)
- **Concurrent agents**: Tested with 10+ agents
- **Message throughput**: ~1000 messages/second
- **Database**: SQLite (suitable for development/small deployments)

For production, consider:
- PostgreSQL instead of SQLite
- Redis Cluster for high availability
- Load balancer for multiple orchestrator instances

## Contributing

When modifying the orchestrator:
1. Keep modules focused (single responsibility)
2. Add type hints to all functions
3. Update this README with API changes
4. Test with multiple concurrent agents

## See Also

- [Main README](../README.md) - Project overview
- [MCP_TOOLS_GUIDE.md](../MCP_TOOLS_GUIDE.md) - MCP integration guide
- [Frontend README](../frontend/README.md) - UI development
