# MCP Tools Framework - Implementation Guide

A comprehensive guide to integrating MCP (Model Context Protocol) servers and tools with AI agents.

## Overview

The MCP tools framework enables agents to execute external tools via MCP servers. The assistant discovers all agent tools and intelligently routes user requests to the appropriate agent.

## Architecture

```
User Request
    ↓
Assistant (discovers all agent tools)
    ↓
Routes to Agent with matching tool
    ↓
Agent executes tool via MCP server
    ↓
Result returned to user
```

## Key Components

### 1. MCP Client

**Location**: `orchestrator/app/action_client.py`

- Fetches OpenAPI specs from MCP servers
- Parses available tools and their parameters
- Executes tools with bearer authentication
- Returns structured results (result/error format)

**Example Usage**:
```python
from app.action_client import MCPActionClient

client = MCPActionClient(
    base_url="https://your-mcp-server.example.com",
    bearer_token="your-token"
)

# List available tools
tools = client.list_actions()

# Execute a tool
result = client.execute_action(
    "/api/actions/get-wikipedia-summary/run",
    {"article_url": "https://en.wikipedia.org/wiki/AI"}
)
```

### 2. Agent Configuration

**Location**: `agent_configs/{agent_name}.json`

Assign MCP tools to an agent by referencing the server name from `action_servers.json`:

```json
{
  "agent_name": "bob",
  "action_server": "email_mcp"
}
```

That's it! The orchestrator will:
1. Look up `email_mcp` in `action_servers.json`
2. Auto-discover all tools from that server's OpenAPI spec
3. Store the tools in the database
4. Make them available to the agent

**Note**: MCP server configuration (URL, auth, etc.) is centralized in `action_servers.json`. See [MCP_SERVERS_CONFIG.md](MCP_SERVERS_CONFIG.md) for details.

### 3. API Endpoints

**Get Agent Tools**:
```bash
GET /agents/{agent_name}/actions
```

**Execute Tool**:
```bash
POST /agents/{agent_name}/actions/execute
{
  "action_id": "get_wikipedia_summary",
  "parameters": {
    "article_url": "https://en.wikipedia.org/wiki/AI"
  }
}
```

**List All Tools**:
```bash
GET /actions/all
```

**Search Tools**:
```bash
GET /actions/search?query=wikipedia
```

### 4. BaseAgent Integration

**Location**: `agentkit/agentkit/base.py`

All agents have tool management methods:

```python
# Load tools from orchestrator (automatic on startup)
agent.load_actions()

# Execute a tool
result = agent.execute_action("tool_id", {"param": "value"})

# Check available tools
tools = agent.list_actions()
has_email = agent.has_action("check_email")
tool = agent.get_action("check_email")
```

### 5. Assistant Intelligence

**Location**: `agents/assistant/`

The assistant:
1. Discovers all agent tools on each request
2. Includes tool information in its system prompt
3. Routes requests to appropriate agents based on tools

**Example System Prompt Section**:
```
## Agent Tools
Some agents have special tools they can execute:

**@bob** (Research Assistant):
  - Get Wikipedia Summary: Retrieves Wikipedia article summary

When users request these tools, delegate to the appropriate agent.
Example: "get wikipedia summary for AI" → route to bob
```

### 6. Worker Agent Execution

**Location**: `agents/worker_agent.py`

Worker agents:
1. Check if request matches any of their tools
2. Extract parameters from natural language using AI
3. Execute the tool via BaseAgent's `execute_action()` method
4. Return results to user
5. Fall back to regular AI if no tool matches

## Usage Flow

### Setting Up Tools for an Agent

1. **Configure MCP Server** (if not already done)

First, add your MCP server to `action_servers.json`. See [MCP_SERVERS_CONFIG.md](MCP_SERVERS_CONFIG.md).

2. **Create Agent Configuration**

Create `agent_configs/{agent_name}.json` referencing the MCP server:

```json
{
  "agent_name": "bob",
  "action_server": "email_mcp"
}
```

Tools will be auto-discovered from the MCP server's OpenAPI spec.

3. **Restart Orchestrator**

```bash
cd orchestrator
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 9000
```

You'll see:
```
🔧 Loaded tool config for agent: bob (1 tools)
```

4. **Agents Auto-Load Tools**

When agents start, they automatically load their tools:
```
[bob] Loaded 1 tool(s)
[bob] 🔧 Tools loaded: ['Get Wikipedia Summary']
```

### Using Tools in Conversation

**Example 1: Direct Request**
```
User: @bob get me a summary of the Wikipedia article about AI
  ↓
Bob: Finds "Get Wikipedia Summary" tool matches
  ↓
Bob: Extracts parameter: article_url
  ↓
Bob: Executes tool via MCP server
  ↓
Bob: ✅ Get Wikipedia Summary completed:
     [Article summary]
```

**Example 2: Via Assistant**
```
User: Get me a Wikipedia summary for Machine Learning
  ↓
Assistant: Discovers Bob has "Get Wikipedia Summary" tool
  ↓
Assistant: @bob please get wikipedia summary for Machine Learning
  ↓
Bob: [Executes tool and returns result]
```

## Advanced Features

### Auto-Discovery from OpenAPI Spec

Auto-generate tool configurations from OpenAPI spec:

```python
from app.action_client import MCPActionClient

client = MCPActionClient(
    base_url="https://your-mcp-server.example.com",
    bearer_token="your-token"
)

# List and print all tools
tools = client.list_actions()
for tool in tools:
    print(json.dumps(tool.to_dict(), indent=2))
```

Copy the output to your agent's configuration file.

### Testing Tools

**Via API**:
```bash
curl -X POST http://localhost:9000/agents/bob/actions/execute \
  -H "Content-Type: application/json" \
  -d '{
    "action_id": "get_wikipedia_summary",
    "parameters": {
      "article_url": "https://en.wikipedia.org/wiki/Python"
    }
  }'
```

**Via Chat**:
```
User: @bob get wikipedia summary for Python programming
```

## Troubleshooting

### Tools Not Loading

**Check orchestrator logs**:
```
🔧 Loaded tool config for agent: bob (1 tools)
```

If not showing:
1. Verify `agent_configs/bob.json` exists
2. Check JSON syntax is valid
3. Ensure agent exists in database
4. Restart orchestrator

### Agent Can't Execute Tools

**Check agent logs**:
```
[BOB] Loaded 1 tool(s)
[BOB] 🔧 Tools loaded: ['Get Wikipedia Summary']
```

If not showing:
1. Verify agent started after orchestrator loaded configs
2. Restart agent

### Tool Execution Fails

**Check for**:
1. Valid bearer token
2. Correct endpoint URL
3. Required parameters provided
4. Network connectivity to MCP server

**Example error**:
```
❌ Error executing Get Wikipedia Summary: 403 Forbidden
```
→ Check bearer token is correct

### Parameter Extraction Fails

The agent uses AI to extract parameters from natural language. If extraction fails:

1. Be more explicit in your request:
   ```
   Instead of: "get wiki summary for AI"
   Try: "get wikipedia summary for https://en.wikipedia.org/wiki/AI"
   ```

2. Check agent logs for extraction details:
   ```
   [BOB] Extracted parameters: {'article_url': '...'}
   ```

## Example: Adding Email Tools

1. **Setup MCP Server** (separate project)

   Create your MCP server with email tools. Example:
   ```python
   @tool
   def check_latest_email():
       """Check the latest unread emails."""
       return {"result": "You have 3 unread emails..."}
   ```

   Ensure it provides an OpenAPI spec at `/openapi.json`.

2. **Configure MCP Server** in `action_servers.json`:
   ```json
   {
     "servers": {
       "email_mcp": {
         "name": "email_mcp",
         "url": "http://localhost:8000",
         "description": "Local MCP server with email tools",
         "auto_discover": true
       }
     }
   }
   ```

3. **Assign Tools to Agent**

   **Option A - Via Assistant:**
   ```
   User: Give bob the email tools
   ```

   **Option B - Manually** create `agent_configs/bob.json`:
   ```json
   {
     "agent_name": "bob",
     "action_server": "email_mcp"
   }
   ```

4. **Restart Orchestrator** to discover tools:
   ```bash
   uvicorn app.main:app --reload --port 9000
   ```

5. **Test**
   ```
   User: check my latest email
   Assistant: @bob please check latest email
   Bob: ✅ Check Latest Email completed:
        You have 3 unread emails...
   ```

## Summary

The MCP tools framework provides:
- ✅ MCP server integration
- ✅ Configuration-based tool assignment
- ✅ Automatic tool discovery by assistant
- ✅ Smart routing based on tools
- ✅ Natural language parameter extraction
- ✅ Comprehensive API for tool management
- ✅ Easy extensibility for new tools

See also: [MCP_SERVERS_CONFIG.md](MCP_SERVERS_CONFIG.md) for server configuration details.
