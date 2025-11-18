# MCP Servers Configuration

This file explains how to configure MCP (Model Context Protocol) servers in `action_servers.json`.

## Overview

The `action_servers.json` file contains centralized configuration for all MCP servers. This approach:
- **Centralizes configuration** - Store URL once, not per agent
- **Simplifies management** - Update once when configuration changes
- **Enables sharing** - Multiple agents can use the same MCP server
- **Auto-discovery** - Actions automatically discovered from OpenAPI specs

## Configuration Format

```json
{
  "servers": {
    "server_name": {
      "name": "server_name",
      "url": "http://localhost:8000",
      "description": "Optional description",
      "auto_discover": true
    }
  }
}
```

## Fields

- **name**: Unique identifier for this server (must match the key in the object)
- **url**: Base URL of the MCP server
- **token**: (Optional) Bearer authentication token if server requires auth - most MCP servers don't need this
- **description**: Optional human-readable description
- **auto_discover**: Whether to automatically fetch tools from OpenAPI spec (recommended: `true`)

## Example: Multiple MCP Servers

```json
{
  "servers": {
    "email_mcp": {
      "name": "email_mcp",
      "url": "http://localhost:8000",
      "description": "Local MCP server with email tools (send-email, read-emails)",
      "auto_discover": true
    },
    "calendar_mcp": {
      "name": "calendar_mcp",
      "url": "http://localhost:8001",
      "description": "Local MCP server with calendar tools",
      "auto_discover": true
    },
    "remote_mcp": {
      "name": "remote_mcp",
      "url": "https://tools.example.com",
      "token": "optional-bearer-token",
      "description": "Remote MCP server (with authentication)",
      "auto_discover": true
    }
  }
}
```

## Authentication (Optional)

Most local MCP servers don't require authentication. If your MCP server requires it:

```json
{
  "servers": {
    "authenticated_mcp": {
      "name": "authenticated_mcp",
      "url": "https://secure-server.example.com",
      "token": "your-bearer-token",
      "description": "Authenticated MCP server",
      "auto_discover": true
    }
  }
}
```

The `token` is optional and only needed if your MCP server requires bearer token authentication.

## Referencing in Agent Configurations

Once MCP servers are defined here, agents reference them by name in their config:

**File**: `agent_configs/bob.json`
```json
{
  "agent_name": "bob",
  "action_server": "email_mcp"
}
```

This tells Bob to use the `email_mcp` server configuration. Actions are automatically discovered from the server's OpenAPI spec.

## Updating Configuration

To update MCP server configuration:

1. Edit `action_servers.json`
2. Update the server details
3. Restart the orchestrator
4. Actions will be automatically rediscovered on startup

No need to update individual agent configurations!

## Loading Order

On orchestrator startup:
1. Load `action_servers.json` first
2. For each server with `auto_discover: true`, fetch OpenAPI spec and discover tools
3. Then load `agent_configs/*.json`
4. Agent configs validate that their referenced server exists
5. Store discovered tools in database linked to each agent

If a server is missing:
```
⚠️  MCP server 'unknown_server' not found for agent 'bob'
```

## Template for New Servers

```json
{
  "servers": {
    "your_server_name": {
      "name": "your_server_name",
      "url": "http://localhost:PORT_NUMBER",
      "description": "Brief description of what tools this server provides",
      "auto_discover": true
    }
  }
}
```

## OpenAPI Requirements

Your MCP server MUST provide an OpenAPI spec at one of these endpoints:
- `/openapi.json` (preferred)
- `/` (root)
- `/api/openapi.json`
- `/docs/openapi.json`

The framework will automatically try these endpoints in order.

## Next Steps

After configuring MCP servers:
1. Create/update agent configs in `agent_configs/`
2. Reference the server by name with `"action_server": "server_name"`
3. Restart orchestrator to discover tools
4. Agents automatically get access to all tools from their assigned server

For more details, see [MCP_INTEGRATION.md](docs/MCP_INTEGRATION.md).
