# Agent Tool Configurations

This directory contains MCP tool configurations for individual agents. Each agent can be assigned tools from MCP (Model Context Protocol) servers.

## Purpose

Agent tool configurations define:
1. **MCP Server Connection** - Which MCP server the agent connects to
2. **Available Tools** - Which tools the agent can execute
3. **Tool Parameters** - Expected parameters for each tool

## Configuration Format

Each agent has a JSON file: `{agent_name}.json`

### Example Configuration

```json
{
  "agent_name": "bob",
  "action_server": {
    "url": "https://your-mcp-server.example.com",
    "token": "your-bearer-token",
    "type": "mcp"
  },
  "actions": [
    {
      "id": "get_wikipedia_summary",
      "name": "Get Wikipedia Summary",
      "description": "Retrieves Wikipedia article summary",
      "endpoint": "/api/actions/get-wikipedia-summary/run",
      "parameters": [
        {
          "name": "article_url",
          "type": "string",
          "description": "URL of the Wikipedia article",
          "required": true
        }
      ],
      "enabled": true
    }
  ]
}
```

## Field Descriptions

### MCP Server Connection

- **url**: Full URL to the MCP server
- **token**: Bearer token for authentication
- **type**: Server type (usually `"mcp"`)

### Tool Definitions

- **id**: Unique tool identifier (from OpenAPI operationId)
- **name**: Human-readable tool name
- **description**: What the tool does
- **endpoint**: API endpoint path for execution
- **parameters**: Array of parameter definitions
  - **name**: Parameter name
  - **type**: Data type (`string`, `number`, `boolean`, etc.)
  - **description**: Parameter description
  - **required**: Whether the parameter is required
- **enabled**: Whether this tool is active (default: `true`)

## How Tools Work

1. **Configuration Loading**
   - Orchestrator loads tool configs on startup
   - Each agent's tools are stored in the database

2. **Agent Startup**
   - Agents query orchestrator for their tools
   - Tools are loaded into agent memory

3. **Tool Execution**
   - User requests a tool via chat
   - Assistant routes to agent with matching tool
   - Agent executes tool via MCP server
   - Result returned to user

## Adding Tools to an Agent

### Method 1: Manual Configuration

1. Create `agent_configs/{agent_name}.json`
2. Define MCP server connection
3. List available tools (see example above)
4. Restart orchestrator

### Method 2: Auto-Discovery

Use the MCP client to auto-discover tools from OpenAPI spec:

```python
from app.action_client import MCPActionClient

client = MCPActionClient(
    base_url="https://your-mcp-server.example.com",
    bearer_token="your-token"
)

# List all tools
tools = client.list_actions()
for tool in tools:
    print(json.dumps(tool.to_dict(), indent=2))
```

Copy the output to your agent's configuration file.

### Method 3: Via Assistant (UI)

```
User: @assistant give bob email tools
Assistant: ✅ Assigned email_mcp to bob
          🔄 Agent restarted - tools are now active!
```

## Tool Assignment Flow

```
1. Create agent_configs/bob.json
2. Restart orchestrator
   → Orchestrator loads tool config
   → Tools stored in database
3. Agent (bob) starts
   → Queries orchestrator for tools
   → Loads tools into memory
4. User requests tool
   → Assistant discovers bob has tool
   → Routes to bob
   → Bob executes tool via MCP server
```

## Example: Email Tools

**Create Configuration:**
```json
{
  "agent_name": "bob",
  "action_server": {
    "url": "https://email-mcp.example.com",
    "token": "your-token",
    "type": "mcp"
  },
  "actions": [
    {
      "id": "check_email",
      "name": "Check Latest Email",
      "description": "Retrieves latest unread emails",
      "endpoint": "/api/actions/check-email/run",
      "parameters": [],
      "enabled": true
    },
    {
      "id": "send_email",
      "name": "Send Email",
      "description": "Sends an email message",
      "endpoint": "/api/actions/send-email/run",
      "parameters": [
        {
          "name": "to",
          "type": "string",
          "description": "Recipient email address",
          "required": true
        },
        {
          "name": "subject",
          "type": "string",
          "description": "Email subject",
          "required": true
        },
        {
          "name": "body",
          "type": "string",
          "description": "Email body",
          "required": true
        }
      ],
      "enabled": true
    }
  ]
}
```

**Usage:**
```
User: @bob check my email
Bob: ✅ Check Latest Email completed:
     You have 3 unread emails...

User: @bob send email to alice@example.com subject "Hello" body "Hi Alice!"
Bob: ✅ Send Email completed:
     Email sent successfully
```

## Troubleshooting

### Tools Not Loading

**Check orchestrator logs:**
```
🔧 Loaded tool config for agent: bob (2 tools)
```

If not showing:
1. Verify `agent_configs/bob.json` exists
2. Check JSON syntax is valid
3. Restart orchestrator

### Agent Can't Execute Tools

**Check agent logs:**
```
[BOB] Loaded 2 tool(s)
[BOB] 🔧 Tools loaded: ['Check Latest Email', 'Send Email']
```

If not showing:
1. Ensure agent started after orchestrator
2. Restart the agent

### Tool Execution Fails

Check for:
1. **Invalid token** - Verify bearer token in configuration
2. **Wrong endpoint** - Check endpoint URL matches MCP server
3. **Missing parameters** - Ensure all required parameters provided
4. **Network issues** - Test connectivity to MCP server

**Example error:**
```
❌ Error executing Send Email: 403 Forbidden
```
→ Check bearer token is correct

## Configuration File Location

- **Development**: `agent_configs/{agent_name}.json`
- **Production**: Same location (committed to repo)

**Note:** This directory should be committed to version control. Tool configurations are part of the agent's capabilities.

## See Also

- [MCP_TOOLS_GUIDE.md](../MCP_TOOLS_GUIDE.md) - Complete MCP integration guide
- [MCP_SERVERS_CONFIG.md](../MCP_SERVERS_CONFIG.md) - MCP server configuration
- [Main README](../README.md) - Project overview
