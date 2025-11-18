# AI Agents - Multi-Agent Orchestration System

> A sophisticated multi-agent system enabling natural conversations with AI agents through @mentions, smart routing, and parallel execution. Optionally extend agents with external tools via MCP (Model Context Protocol) servers.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Node 16+](https://img.shields.io/badge/node-16+-green.svg)](https://nodejs.org/)

---

## ✨ Features

- **🎯 Smart @Mention Routing** - Direct messages to specific agents or broadcast to multiple agents
- **🔒 Conversation Locking** - Lock conversations to specific agents for context continuity
- **🤖 Agent Management** - Create, start, stop, and delete agents dynamically from the UI
- **🛠️ MCP Tool Integration (Optional)** - Extend agents with external tools via your own MCP servers
- **⚡ Parallel Execution** - Multiple agents can process tasks simultaneously
- **💬 Natural Language** - Conversational interface with autocomplete and typing indicators
- **📝 Conversation History** - Persistent chat history across sessions
- **🎨 Agent Themes** - Each agent has unique colors and icons

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **Node.js 16+**
- **Redis** (for message pub/sub)
- **OpenAI API Key**

### Installation

1. **Clone and setup environment**:
\`\`\`bash
git clone https://github.com/yourusername/ai-agents.git
cd ai-agents

# Create .env file with your OpenAI API key
echo "OPENAI_API_KEY=your_key_here" > .env
echo "ORCHESTRATOR_URL=http://localhost:9000" >> .env
\`\`\`

2. **Install orchestrator**:
\`\`\`bash
cd orchestrator
uv venv
source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate
uv pip install -e .
deactivate
\`\`\`

3. **Install assistant agent**:
\`\`\`bash
cd ../agents/assistant
uv venv
source .venv/bin/activate
uv pip install -e ../../agentkit
uv pip install -e .
deactivate
\`\`\`

4. **Install frontend**:
\`\`\`bash
cd ../../frontend
npm install
\`\`\`

### Running the System

Open **2 terminals**:

**Terminal 1 - Orchestrator**:
\`\`\`bash
cd orchestrator
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 9000
\`\`\`

**Terminal 2 - Frontend**:
\`\`\`bash
cd frontend
npm run dev
\`\`\`

Access the UI at **http://localhost:5173**

The assistant agent will start automatically when you first send a message.

> **📘 Note:** The system is fully functional with just the core components above. **MCP tool integration is completely optional** and allows you to extend agents with custom external tools. See the [MCP Tool Integration](#-mcp-tool-integration) section if you want to add this later. **MCP servers are NOT included** in this repository - you'll need to set up your own.

For a more detailed beginner-friendly guide, see **[GETTING_STARTED.md](GETTING_STARTED.md)**.

---

## 💬 Usage Examples

### Basic Conversation
\`\`\`
hello
\`\`\`
→ Routes to the assistant agent (default)

### Single Agent (Locks Conversation)
\`\`\`
@bob flip a coin
what about heads?
\`\`\`
→ First message routes to bob and locks conversation  
→ Second message automatically goes to bob (locked)

### Multiple Agents (Parallel Broadcast)
\`\`\`
@bob @frank both guess a number
\`\`\`
→ Both agents respond simultaneously

### Delegation (via Assistant)
\`\`\`
@assistant ask @bob and @frank to introduce themselves
\`\`\`
→ Assistant coordinates communication with multiple agents

### Agent Management
\`\`\`
@assistant create a new agent called translator with translation capability
@assistant start the researcher agent
@assistant stop all agents
\`\`\`

### Unlocking Conversations
- **Mention multiple agents**: \`@bob @frank hello\` (clears lock)
- **Click "Unlock" button** in the UI

---

## 🏗️ Architecture

\`\`\`
┌─────────────────────────────────────────┐
│     Frontend (React + TypeScript)       │
│                                         │
│  • Chat UI with @mention autocomplete  │
│  • Agent dashboard & management        │
│  • Typing indicators & themes          │
└──────────────┬──────────────────────────┘
               │ WebSocket
               ↓
┌─────────────────────────────────────────┐
│   Orchestrator (FastAPI + Redis)        │
│                                         │
│  • Message routing & agent lifecycle   │
│  • MCP tool discovery & execution      │
│  • Session & state management          │
└──────────────┬──────────────────────────┘
               │ Redis Pub/Sub
               ↓
┌─────────────────────────────────────────┐
│         Agents (Python + AgentKit)      │
│                                         │
│  • Assistant (coordinator)             │
│  • Worker agents (specialized tasks)   │
│  • MCP tool integration                │
└─────────────────────────────────────────┘
\`\`\`

### Routing Modes

1. **Delegation**: \`@assistant ask @other\` → Only assistant receives
2. **Parallel Broadcast**: \`@agent1 @agent2\` → Both receive simultaneously
3. **Single Lock**: \`@agent\` → Routes to agent and locks conversation
4. **Default**: No mention → Routes to locked agent or assistant

---

## 🛠️ MCP Tool Integration (Optional)

> **⚠️ Important:** MCP servers are **NOT included** in this repository. This section is for users who want to extend their agents with custom external tools by connecting to their own MCP (Model Context Protocol) servers. The system works perfectly without this feature.

Agents can execute external tools via MCP servers that you provide. Tools are auto-discovered and intelligently routed by the assistant.

### Example: Wikipedia Tool

**1. Configure agent with MCP tool**:
\`\`\`json
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
\`\`\`

**2. Use in conversation**:
\`\`\`
User: @bob get me a Wikipedia summary for Artificial Intelligence

Bob: ✅ Get Wikipedia Summary completed:
     [Article summary content]
\`\`\`

### Configuration Files

- **MCP Servers**: \`action_servers.json\` (centralized server configuration)
- **Agent Tools**: \`agent_configs/{agent_name}.json\` (per-agent tool assignments)

### Documentation

- **[MCP_TOOLS_GUIDE.md](MCP_TOOLS_GUIDE.md)** - Complete MCP integration guide
- **[MCP_SERVERS_CONFIG.md](MCP_SERVERS_CONFIG.md)** - Server configuration reference

---

## 📁 Project Structure

\`\`\`
ai-agents/
├── orchestrator/           # FastAPI backend & orchestration
│   ├── app/
│   │   ├── main.py        # Main orchestrator (routing, lifecycle)
│   │   ├── agent_lifecycle.py  # Agent start/stop/create/delete
│   │   ├── routing.py     # @mention extraction & routing
│   │   ├── action_management.py  # MCP tool management
│   │   └── action_client.py     # MCP client
│   └── agents.db          # SQLite database
│
├── agents/                # Agent implementations
│   ├── assistant/         # Main coordinator agent (refactored)
│   │   ├── main.py       # Core agent class (242 lines, 86% reduced)
│   │   ├── agent_operations.py   # Agent lifecycle (452 lines)
│   │   ├── ai_functions.py       # AI completions (338 lines)
│   │   ├── collaboration.py      # Multi-agent coordination (391 lines)
│   │   └── message_handling.py   # Message routing (481 lines)
│   └── worker_agent.py    # Generic worker agent template
│
├── agentkit/              # Shared agent framework
│   └── agentkit/
│       ├── base.py        # BaseAgent class
│       ├── messaging.py   # Redis pub/sub
│       ├── ai.py          # OpenAI client
│       └── discovery.py   # Agent discovery
│
├── frontend/              # React UI
│   └── src/
│       ├── components/
│       │   ├── Chat.tsx   # Main chat interface
│       │   └── Dashboard.tsx  # Agent management
│       └── App.tsx
│
├── runbooks/              # Agent capability definitions (Markdown)
│   ├── assistant.md
│   └── *.md
│
├── agent_configs/         # Agent-specific tool configurations (JSON)
│   └── *.json
│
└── action_servers.json    # MCP server configurations
\`\`\`

---

## 🔧 API Endpoints

### WebSocket
| Endpoint | Description |
|----------|-------------|
| \`WS /ws/{session_id}\` | Real-time chat communication |

### Agent Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| \`GET\` | \`/agents\` | List all agents |
| \`POST\` | \`/agents/start\` | Start an agent |
| \`POST\` | \`/agents/stop\` | Stop an agent |
| \`POST\` | \`/agents/create\` | Create new agent |
| \`POST\` | \`/agents/delete\` | Delete agent |
| \`GET\` | \`/agents/runbooks\` | Get agent runbooks |

### MCP Tools
| Method | Endpoint | Description |
|--------|----------|-------------|
| \`GET\` | \`/agents/{name}/actions\` | Get agent's tools |
| \`POST\` | \`/agents/{name}/actions/execute\` | Execute a tool |
| \`GET\` | \`/actions/all\` | List all agent tools |
| \`GET\` | \`/actions/search?query=...\` | Search tools |

See **[orchestrator/README.md](orchestrator/README.md)** for complete API documentation.

---

## 🎯 Development

### Adding a New Agent

1. **Create runbook** defining agent capabilities:
\`\`\`bash
# Create runbooks/myagent.md
## Agent: MyAgent
## Job Title: Data Analyst

Specialized in data analysis and visualization.

### Capabilities
- **Data Analysis**: Analyze datasets and generate insights
- **Visualization**: Create charts and graphs
\`\`\`

2. **Create agent via UI** or API:
\`\`\`bash
POST /agents/create
{
  "name": "myagent",
  "role": "Data Analyst",
  "capabilities": [
    {
      "name": "Data Analysis",
      "description": "Analyze datasets"
    }
  ]
}
\`\`\`

3. **Optionally add MCP tools**:
\`\`\`bash
# Create agent_configs/myagent.json with tool configuration
\`\`\`

### Modifying Routing Logic

- **Backend**: \`orchestrator/app/routing.py\` - Extract mentions, route messages
- **Frontend**: \`frontend/src/components/Chat.tsx\` - Handle @mentions, autocomplete

### Agent Implementation

- **Base class**: \`agentkit/agentkit/base.py\` - Core agent functionality
- **Example**: \`agents/assistant/\` - Full-featured coordinator
- **Template**: \`agents/worker_agent.py\` - Generic worker agent

---

## 📚 Documentation

- **[CURRENT_FEATURES.md](CURRENT_FEATURES.md)** - Comprehensive feature documentation
- **[MCP_TOOLS_GUIDE.md](MCP_TOOLS_GUIDE.md)** - MCP tool integration guide
- **[MCP_SERVERS_CONFIG.md](MCP_SERVERS_CONFIG.md)** - MCP server configuration
- **[orchestrator/README.md](orchestrator/README.md)** - Orchestrator API reference
- **[frontend/README.md](frontend/README.md)** - Frontend development guide

---

## 🐛 Troubleshooting

### Agent Not Responding?
- Check dashboard - agent should show "running"
- System auto-starts agents when @mentioned
- Check browser console for WebSocket errors
- Verify Redis is running

### Lock Not Working?
- Single @mention locks: \`@agent message\`
- Multiple @mentions unlock: \`@agent1 @agent2 message\`
- Click "Unlock" button in UI to manually reset

### Tools Not Executing?
- Verify \`agent_configs/{agent}.json\` exists
- Check MCP server URL and bearer token
- Ensure agent restarted after adding tools
- Check orchestrator logs for tool discovery

### WebSocket Connection Issues?
- Ensure orchestrator is running on port 9000
- Check \`ORCHESTRATOR_URL\` in \`.env\`
- Clear browser cache and reload

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details

---

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/), [React](https://react.dev/), and [Redis](https://redis.io/)
- Powered by [OpenAI](https://openai.com/) language models
- MCP integration for extensible tool support

---

**Made with ❤️ for the AI community**
