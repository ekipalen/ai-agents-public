# AI Agents - Multi-Agent Chat System

A sophisticated multi-agent system enabling natural conversations with multiple AI agents through @mentions, smart routing, and parallel execution.

---

## Core Features

### 1. Smart Agent Routing

The system supports three routing modes based on how you mention agents:

#### Delegation Mode
**Trigger:** First mention is `@assistant`
**Behavior:** Only assistant receives the message and coordinates with other agents

```
User: @assistant ask @linda and @frank to guess a number
→ Routes to: assistant only
→ Assistant receives: "ask @linda and @frank to guess a number"
→ Assistant responds: "@linda please guess..." "@frank please guess..."
→ System routes assistant's @mentions to linda and frank
```

#### Parallel Broadcast Mode
**Trigger:** Multiple agents mentioned (not starting with @assistant)
**Behavior:** All mentioned agents receive the message simultaneously

```
User: @bob @frank both guess a number between 1-10
→ Routes to: bob AND frank (parallel)
→ Both receive: "both guess a number between 1-10"
→ Both respond independently
→ UI shows both typing indicators
→ Lock clears (returns to assistant)
```

#### Single Agent Lock
**Trigger:** Single agent mentioned
**Behavior:** Routes to that agent and locks conversation to them

```
User: @linda flip a coin
→ Routes to: linda
→ Locks to: linda
→ Next message without @mention goes to linda
```

#### Default Routing
**Trigger:** No @mention
**Behavior:** Routes to currently locked agent (or assistant if not locked)

```
User: hello
→ Routes to: assistant (default)
```

---

### 2. Agent Locking System

**Visual Lock Indicator:**
```
When unlocked (assistant):
┌──────────────┐
│ 🤖 assistant │              Type @ to mention agents
└──────────────┘

When locked (e.g., linda):
┌─────────────┐  ┌────────┐
│ 👩 linda    │  │ Unlock │    Type @ to mention agents
└─────────────┘  └────────┘
(gradient badge)  (button)
```

**Lock Behavior:**
- Lock to agent: `@agent_name message` (single mention)
- Switch lock: `@different_agent message`
- Clear lock: `@agent1 @agent2 message` (parallel broadcast)
- Manual unlock: Click "Unlock" button
- Stay locked: Send message without @mention

---

### 3. Typing Indicators

**Smart Timing:**
- Appear **1 second after** you send a message
- Your message renders first (smooth UX)
- If agent responds in <1 second, typing indicator never shows
- Cleared automatically when agent responds
- Shows all agents typing in parallel broadcast mode

**Visual:**
```
linda is typing... ●●●
```

---

### 4. Agent @Mention Syntax

**Examples:**

| Input | Routing | Lock Behavior |
|-------|---------|---------------|
| `@linda hi` | linda | Locks to linda |
| `@bob @frank guess` | bob, frank | Unlocks (parallel) |
| `@assistant ask @ben` | assistant | Locks to assistant |
| `hello` | (locked agent) | Stays locked |
| `hello` | assistant | (no lock) |

**Nested Mentions:**
```
@assistant ask @linda and @frank to each guess a number
→ Assistant receives: "ask @linda and @frank to each guess a number"
→ Assistant can parse @linda and @frank from the message
→ Assistant responds with @mentions to delegate
```

---

### 5. Agent Autocomplete

**Trigger:** Type `@` in the input field

**Features:**
- Shows all available running agents
- Keyboard navigation: ↑↓ to select, Tab/Enter to insert
- Click to select
- Auto-hides when you delete the `@`

**Visual:**
```
Available agents (↑↓ Tab/Enter):
╔═════════════╗
║ 🤖 @assistant ║  ← Selected (blue)
║ 👩 @linda   ║
║ 👨 @bob     ║
╚═════════════╝
```

---

### 6. Agent Management

**From UI Dashboard:**
- **Create Agent:** Click "Create Agent", provide name + capabilities
- **Start Agent:** Click "Start" button
- **Stop Agent:** Click "Stop" button
- **Delete Agent:** Click "Delete" button (removes agent + runbook)

**Auto-start:**
- When you @mention a stopped agent, it auto-starts
- System waits for agent to be ready before sending message
- Shows loading feedback during startup

---

### 7. Conversation Persistence

**Automatic Saving:**
- All messages saved to browser localStorage
- Per-session conversation history
- Restored when you refresh the page

**Clearing:**
- Click "🗑️ Clear Chat" button
- Clears both frontend and backend history
- Auto-clears on orchestrator restart

**Backend Storage:**
```python
chat_histories = {
    "session_id": {
        "assistant": [...messages],
        "linda": [...messages],
        "bob": [...messages]
    }
}
```
Each agent maintains separate conversation history for context.

---

### 8. Agent Themes & Visual Identity

Each agent has unique visual styling:

| Agent | Icon | Color | Gradient |
|-------|------|-------|----------|
| assistant | 🤖 | Blue | from-blue-500 to-blue-600 |
| bob | 👨‍💼 | Green | from-green-500 to-green-600 |
| linda | 👩 | Pink | from-pink-500 to-pink-600 |
| frank | 👨‍🏫 | Purple | from-purple-500 to-purple-600 |
| john | 👨‍🔬 | Amber | from-amber-500 to-amber-600 |
| mary | 👩‍💻 | Rose | from-rose-500 to-rose-600 |
| lisa | 👩‍🎨 | Cyan | from-cyan-500 to-cyan-600 |

**Applied to:**
- Lock indicator badge (gradient background)
- Dashboard agent cards
- Message prefixes in chat

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────┐
│                     Frontend                        │
│  (React/TypeScript + WebSocket)                     │
│  - Chat.tsx: Main chat interface                    │
│  - AgentDashboard.tsx: Agent management UI          │
└──────────────────┬──────────────────────────────────┘
                   │ WebSocket
                   │ /ws/{session_id}
┌──────────────────▼──────────────────────────────────┐
│                 Orchestrator                        │
│  (FastAPI + Redis)                                  │
│  - WebSocket routing                                │
│  - @mention extraction & routing                    │
│  - Agent lifecycle management                       │
│  - Message distribution                             │
└──────────────────┬──────────────────────────────────┘
                   │ Redis pub/sub
                   │ agent:{name}:inbox
┌──────────────────▼──────────────────────────────────┐
│                   Agents                            │
│  - Assistant (coordinator)                          │
│  - Worker agents (specialized tasks)                │
│  - AgentKit (base framework)                        │
└─────────────────────────────────────────────────────┘
```

### Message Flow

**Example: Parallel Broadcast**
```
User: "@bob @frank both guess a number"
  ↓
Frontend: Extracts mentions ["bob", "frank"]
  ↓
WebSocket → Orchestrator
  ↓
Orchestrator: Detects parallel broadcast (2 agents, not @assistant)
  ↓
Routes to both:
  ├→ agent:bob:inbox {"messages": [...], "content": "both guess a number"}
  └→ agent:frank:inbox {"messages": [...], "content": "both guess a number"}
  ↓
Both agents process simultaneously
  ↓
[Bob]: 7
[Frank]: 4
```

**Example: Delegation**
```
User: "@assistant ask @linda to flip a coin"
  ↓
Orchestrator: Detects delegation (first mention = @assistant)
  ↓
Routes ONLY to assistant:
  agent:assistant:inbox {"content": "ask @linda to flip a coin"}
  ↓
Assistant receives nested @mention preserved
  ↓
Assistant responds: "@linda please flip a coin"
  ↓
Orchestrator detects @mention in assistant's response
  ↓
Routes to linda:
  agent:linda:inbox {"content": "please flip a coin"}
  ↓
[Linda]: Heads!
```

---

## API Endpoints

### Agent Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/agents` | List all agents with status |
| GET | `/agents/available` | List available agent names (for autocomplete) |
| POST | `/agents/start` | Start agent by name |
| POST | `/agents/{id}/stop` | Stop running agent |
| POST | `/agents/delete` | Delete agent + runbook |
| POST | `/agents/create` | Create new agent with capabilities |
| GET | `/agents/runbooks` | Get all agent runbooks |

### Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| WS | `/ws/{session_id}` | WebSocket for real-time chat |
| POST | `/chat/{session_id}/clear` | Clear conversation history |

---

## Directory Structure

```
ai-agents/
├── orchestrator/
│   └── app/
│       ├── main.py          # FastAPI orchestrator
│       ├── models.py        # Database models
│       └── database.py      # DB connection
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── Chat.tsx           # Main chat interface
│       │   └── AgentDashboard.tsx # Agent management
│       ├── lib/
│       │   └── agentTheme.ts      # Agent visual themes
│       └── config/
│           └── api.ts             # API/WebSocket URLs
├── agentkit/                # Shared agent framework
│   └── agentkit/
│       ├── base.py          # BaseAgent class
│       └── messaging.py     # Redis messaging
├── agents/                  # Agent implementations
│   ├── assistant/           # Main coordinator
│   │   └── main.py
│   └── worker_agent.py      # Unified worker for specialized agents
└── runbooks/                # Agent capability definitions (markdown)
    ├── assistant.md
    ├── bob.md
    ├── linda.md
    └── ...
```

---

## Known Behaviors

### LLM Determinism

**Observation:** Multiple agents sometimes give identical responses to simple prompts:
- "guess a number 1-10" → Most say "7"
- "flip a coin" → Slight bias toward "Heads"

**Why This Happens:**
- LLMs use statistical patterns from training data
- Humans perceive "7" as the most random number
- Without explicit randomness, LLMs replicate human biases
- Each agent DOES receive the message independently (verified)

**This is LLM behavior, not a system bug:**
- ✅ Routing works correctly (parallel execution)
- ✅ No shared state between agents
- ✅ Separate conversation histories
- ❌ LLM temperature/sampling causes similar outputs

**Solutions (future):**
- Increase LLM temperature for random tasks
- Add unique random seeds per agent at startup
- Update prompts: "Vary your responses, don't default to 7"
- Inject system entropy/time for true randomness

---

## Performance Optimizations

**Typing Indicator Delay:**
- 1-second delay prevents visual glitching
- Allows user message to render first
- Cleared immediately when agent responds
- Timeouts cleaned up to prevent memory leaks

**WebSocket Connection:**
- Single persistent connection per session
- No reconnection on agent switching
- Handles multiple agents concurrently

**Conversation History:**
- Per-agent context isolation
- Efficient localStorage usage
- Auto-cleanup on orchestrator restart

---

## Development

### Prerequisites
- Python 3.10+
- Node.js 16+
- Redis Server
- OpenAI API key

### Setup
```bash
# Set environment
echo "OPENAI_API_KEY=your_key" > .env

# Install orchestrator
cd orchestrator && uv venv && source .venv/bin/activate
uv pip install -e . && deactivate

# Install assistant agent
cd ../agents/assistant && uv venv && source .venv/bin/activate
uv pip install -e ../../agentkit && uv pip install -e . && deactivate

# Install frontend
cd ../../frontend && npm install
```

### Run
```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Start orchestrator
cd orchestrator && source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 3: Start frontend
cd frontend && npm run dev
```

### Access
- Frontend: http://localhost:5173
- API: http://localhost:8000
- WebSocket: ws://localhost:8000/ws/main

---

## Tips & Tricks

**Quick Agent Switching:**
```
@linda hi      → Lock to linda
@bob hello     → Switch to bob
@frank sup     → Switch to frank
```

**Parallel Tasks:**
```
@bob @frank @linda all of you introduce yourselves
→ All three respond simultaneously
```

**Complex Delegation:**
```
@assistant ask @bob to help @frank with a math problem
→ Assistant coordinates the collaboration
```

**Stay Locked:**
```
@linda flip a coin
heads or tails?          ← Still goes to linda
flip again               ← Still goes to linda
```

**Clear Lock:**
```
[Locked to linda]
@bob @frank guess       → Unlocks, goes to bob & frank
```

---

## Troubleshooting

**Agent not responding:**
- Check if agent is running in dashboard
- System auto-starts mentioned agents
- Check browser console for WebSocket errors

**Typing indicator stuck:**
- Refresh page
- Check if agent crashed (dashboard shows status)
- Indicators auto-clear after 1 second if agent doesn't respond

**Lock not working:**
- Verify single agent mention (not 2+)
- Check lock indicator above input field
- Click "Unlock" to reset to assistant

**@mention not recognized:**
- Use lowercase agent names
- No spaces: `@linda` not `@ linda`
- Check autocomplete for valid agent names

---

## License

MIT
