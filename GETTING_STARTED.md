# Getting Started with AI Agents

Welcome! This guide will walk you through setting up and using the AI Agents multi-agent system, step by step. No prior experience required.

## 📖 What is AI Agents?

AI Agents is a system that lets you chat with multiple AI assistants at once. Think of it like a group chat where you can:
- Talk to different AI agents with specialized skills
- Ask one agent or multiple agents for help
- Create your own custom agents
- Have agents work together on complex tasks

**Important:** This is a complete, working system without any external dependencies beyond the basics (Redis, OpenAI API). The optional MCP tool integration mentioned in the main README is for advanced users who want to extend agents with custom tools - you can skip that entirely.

---

## 🎯 What You'll Build

By the end of this guide, you'll have:

1. A running AI multi-agent chat system
2. A web interface to chat with agents
3. The ability to create custom agents with specialized roles
4. Understanding of how agents communicate and collaborate

**Time estimate:** 15-30 minutes

---

## 📋 Prerequisites Explained

Before we start, you'll need to install these tools. Don't worry - we'll explain what each one does!

### 1. Python 3.10 or higher

**What it is:** The programming language used for the backend (orchestrator and agents).

**Check if you have it:**
```bash
python3 --version
```

**Install if needed:**
- **macOS/Linux:** Usually pre-installed. If not, use your package manager.
- **Windows:** Download from [python.org](https://www.python.org/downloads/)

### 2. Node.js 16 or higher

**What it is:** JavaScript runtime used for the frontend (web interface).

**Check if you have it:**
```bash
node --version
```

**Install if needed:**
- Download from [nodejs.org](https://nodejs.org/)

### 3. Redis

**What it is:** A message broker that helps agents communicate with each other in real-time.

**Install:**
- **macOS:** `brew install redis`
- **Ubuntu/Debian:** `sudo apt-get install redis-server`
- **Windows:** Download from [redis.io/download](https://redis.io/download)

### 4. OpenAI API Key

**What it is:** Your credential to use OpenAI's language models (GPT-4, etc.). This is what powers the AI intelligence.

**Get your key:**
1. Go to [platform.openai.com](https://platform.openai.com/)
2. Sign up or log in
3. Go to API Keys section
4. Create a new API key
5. Copy it somewhere safe - you'll need it in a moment

**Cost:** OpenAI charges per use. Typical conversations cost a few cents. You'll need to add payment info to your OpenAI account.

### 5. uv (Python package installer)

**What it is:** A fast Python package installer (alternative to pip).

**Install:**
```bash
pip install uv
```

Or follow instructions at [github.com/astral-sh/uv](https://github.com/astral-sh/uv)

---

## 🚀 Installation

### Step 1: Clone the Repository

Open your terminal and run:

```bash
git clone https://github.com/yourusername/ai-agents.git
cd ai-agents
```

This downloads the code to your computer and opens the project folder.

### Step 2: Set Up Your OpenAI API Key

Create a configuration file with your API key:

```bash
echo "OPENAI_API_KEY=your_actual_key_here" > .env
echo "ORCHESTRATOR_URL=http://localhost:9000" >> .env
```

**Replace** `your_actual_key_here` with your real OpenAI API key!

**What this does:** Creates a `.env` file that stores your secret API key. The system reads this file when it starts.

### Step 3: Install the Orchestrator

The orchestrator is the "traffic controller" that routes messages between agents.

```bash
cd orchestrator
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
deactivate
cd ..
```

**What this does:**
1. Creates a virtual environment (isolated Python installation)
2. Activates it
3. Installs the orchestrator and its dependencies
4. Deactivates the environment
5. Returns to the main folder

### Step 4: Install the Assistant Agent

The assistant is the "coordinator" agent that helps route your requests.

```bash
cd agents/assistant
uv venv
source .venv/bin/activate
uv pip install -e ../../agentkit
uv pip install -e .
deactivate
cd ../..
```

**What this does:**
1. Creates a virtual environment for the agent
2. Installs the shared agent framework (agentkit)
3. Installs the assistant agent
4. Returns to the main folder

### Step 5: Install the Frontend

The frontend is the web interface you'll use to chat with agents.

```bash
cd frontend
npm install
cd ..
```

**What this does:** Installs all the JavaScript packages needed for the web interface.

---

## ▶️ Starting the System

You'll need **3 terminal windows** open. Don't close any of them while using the system!

### Terminal 1: Start Redis

```bash
redis-server
```

**What you'll see:**
```
Ready to accept connections
```

**Leave this running.** Redis needs to stay active for agents to communicate.

### Terminal 2: Start the Orchestrator

```bash
cd orchestrator
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 9000
```

**What you'll see:**
```
INFO:     Uvicorn running on http://0.0.0.0:9000
```

**Leave this running.** The orchestrator manages all your agents.

### Terminal 3: Start the Frontend

```bash
cd frontend
npm run dev
```

**What you'll see:**
```
Local:   http://localhost:5173/
```

**Leave this running.** This serves the web interface.

---

## 🎉 Your First Conversation

1. **Open your browser** and go to: `http://localhost:5173`

2. **You'll see** a chat interface with a sidebar showing agents.

3. **Type a message:**
   ```
   Hello! Can you help me?
   ```

4. **Press Enter.** The assistant agent will automatically start (if not already running) and respond!

**What's happening behind the scenes:**
- Your message goes to the frontend
- Frontend sends it via WebSocket to the orchestrator
- Orchestrator routes it to the assistant agent
- Assistant processes it using OpenAI and responds
- Response appears in your chat

---

## 🤖 Creating Your First Custom Agent

Let's create an agent that specializes in creative writing!

### Method 1: Via the Chat Interface

1. **Type this message:**
   ```
   @assistant create a new agent called writer with creative writing capability
   ```

2. **The assistant will:**
   - Create the agent
   - Generate a runbook (instruction manual) for it
   - Show you a confirmation

3. **Check the dashboard:**
   - Click "Dashboard" in the UI
   - You'll see "writer" listed as "stopped"

4. **Start your new agent:**
   - Click "Start" next to the writer agent
   - Or send: `@assistant start the writer agent`

5. **Talk to your agent:**
   ```
   @writer write me a short poem about coding
   ```

### Method 2: Via the Dashboard

1. **Click "Dashboard"** in the UI

2. **Click "Create Agent"** button

3. **Fill in the form:**
   - **Name:** writer
   - **Role:** Creative Writing Specialist
   - **Capabilities:**
     - Name: Creative Writing
     - Description: Write poems, stories, and creative content

4. **Click "Create"**

5. **Start the agent** by clicking "Start" next to it

---

## 💡 Understanding @Mentions

The `@` symbol is how you talk to specific agents.

### Examples:

**Talk to one agent:**
```
@writer write a haiku about AI
```

**Talk to multiple agents at once:**
```
@writer @assistant both of you give me ideas for a story
```

**When you don't use @:**
```
what's the weather like?
```
→ Goes to the assistant (default) or whichever agent you're locked to

### Auto-complete

Start typing `@` and you'll see a list of available agents:
- Use ↑ and ↓ arrows to select
- Press Tab or Enter to choose
- Press Esc to cancel

---

## 🔒 Understanding Conversation Locking

When you mention ONE agent, the conversation "locks" to that agent.

**Example:**

```
You: @writer tell me a story
Writer: Once upon a time...

You: make it scarier
Writer: [continues the story with a scary twist]
```

The second message automatically went to `writer` because you're "locked" to that conversation.

**To unlock:**
- Mention multiple agents: `@writer @assistant both help me`
- Click the "Unlock" button in the UI
- Just send a message to a different agent

**Why is this useful?**
- Keeps context with one agent for multi-turn conversations
- You don't need to keep typing `@agent` for every follow-up
- Natural conversation flow

---

## 🎨 Agent Management Commands

Ask the assistant to help manage agents:

**See all agents:**
```
@assistant list all agents
```

**Start an agent:**
```
@assistant start the writer agent
```

**Stop an agent:**
```
@assistant stop the writer agent
```

**Delete an agent:**
```
@assistant delete the writer agent
```

**See agent capabilities:**
```
@assistant what can the writer agent do?
```

---

## 🔍 What's Happening Under the Hood?

Here's a simplified view of how everything works:

```
You type in the browser
    ↓
Frontend (React) sends message via WebSocket
    ↓
Orchestrator receives message
    ↓
Orchestrator extracts @mentions
    ↓
Orchestrator routes to correct agent(s)
    ↓
Agent processes message using OpenAI
    ↓
Agent sends response back
    ↓
You see the response in your browser
```

**All communication happens through Redis pub/sub:**
- Agents subscribe to their name channel
- Orchestrator publishes messages to agent channels
- Agents publish responses back

---

## 📂 Understanding the File Structure

```
ai-agents/
├── .env                    # Your API key (NEVER commit this!)
├── orchestrator/           # The traffic controller
│   ├── agents.db          # Database of agents
│   └── app/               # Orchestrator code
├── agents/
│   └── assistant/         # The coordinator agent
├── agentkit/              # Shared code for all agents
├── frontend/              # Web interface
├── runbooks/              # Agent instruction manuals (.md files)
└── agent_configs/         # Optional: MCP tool configurations
```

**What you might want to edit:**
- `runbooks/*.md` - Customize agent behaviors
- `.env` - Change API keys or settings
- Frontend code if you want to customize the UI

**What to leave alone:**
- `orchestrator/app/` - Core routing logic
- `agentkit/` - Shared agent framework
- `agents/assistant/` - Coordinator logic

---

## 🔧 Optional: Adding MCP Tools (Advanced)

> **Skip this section if you're just getting started!** The system works perfectly without this.

MCP (Model Context Protocol) lets you give agents access to external tools like:
- Checking email
- Searching Wikipedia
- Running code
- Accessing APIs

**Important:**
- MCP servers are **NOT included** in this repo
- You need to set up your own MCP server
- This is an advanced feature for extending agent capabilities

**If you want to explore this later:**
1. Read **[MCP_TOOLS_GUIDE.md](docs/MCP_TOOLS_GUIDE.md)**
2. Set up your own MCP server (separate project)
3. Configure agents to use your tools

---

## 🐛 Common Issues & Solutions

### Issue: "Connection refused" when opening the UI

**Solution:**
- Make sure all 3 terminals are running (Redis, Orchestrator, Frontend)
- Check the terminal outputs for errors
- Try restarting each component

### Issue: "OpenAI API error" or "Unauthorized"

**Solution:**
- Check your `.env` file has the correct API key
- Make sure you've added payment info to your OpenAI account
- Restart the orchestrator after changing `.env`

### Issue: Agent not responding

**Solution:**
- Check the Dashboard - is the agent running?
- Look at the orchestrator terminal - any errors?
- Try stopping and starting the agent
- Check that Redis is running

### Issue: "Module not found" errors

**Solution:**
- Make sure you ran all the installation steps
- Try re-running the install commands
- Check you activated the virtual environment before installing

### Issue: Agent keeps saying "I'm starting..."

**Solution:**
- The assistant agent needs to be started first
- Send any message and it will auto-start
- Or manually start it from the Dashboard

### Issue: Changes to runbooks not taking effect

**Solution:**
- Restart the agent after modifying its runbook
- Or use: `@assistant restart the [agent] agent`

---

## 📚 Next Steps

Now that you have the basics working, here's what to explore next:

### 1. Experiment with Agent Collaboration

Try having multiple agents work together:
```
@assistant ask @writer and @editor to collaborate on a short story
```

### 2. Create Specialized Agents

Ideas for agents to create:
- **Researcher:** Finds and summarizes information
- **Coder:** Helps with programming questions
- **Editor:** Reviews and improves writing
- **Translator:** Translates between languages
- **Analyst:** Analyzes data and provides insights

### 3. Customize Agent Behaviors

Edit the runbook files in `runbooks/` to change how agents behave:
```markdown
## Agent: Writer
## Job Title: Creative Writing Expert

You are a creative writing expert specializing in:
- Poetry
- Short stories
- Character development

### Capabilities
- **Write Poetry:** Create poems in various styles
...
```

### 4. Learn the API

Explore the REST API endpoints:
- `http://localhost:9000/docs` - Interactive API documentation
- Read `orchestrator/README.md` for endpoint details

### 5. Explore Advanced Features

- **Parallel execution:** Have multiple agents work simultaneously
- **Conversation history:** See how context is maintained
- **Typing indicators:** Watch agents "think"
- **Agent themes:** Each agent has unique colors

### 6. Read the Documentation

- **[README.md](README.md)** - Main project overview
- **[orchestrator/README.md](orchestrator/README.md)** - API reference
- **[frontend/README.md](frontend/README.md)** - UI development
- **[CURRENT_FEATURES.md](docs/CURRENT_FEATURES.md)** - All features explained

---

## 🎓 Understanding Key Concepts

### Orchestrator
The central hub that:
- Manages agent lifecycle (start/stop/create/delete)
- Routes messages between frontend and agents
- Maintains the agents database
- Handles WebSocket connections

### Agents
Independent AI assistants that:
- Subscribe to Redis channels
- Process messages using OpenAI
- Have specialized roles and capabilities
- Can collaborate with other agents

### Runbooks
Markdown files that define:
- Agent role and personality
- Capabilities and skills
- Example usage patterns
- Collaboration guidelines

### Redis Pub/Sub
Messaging system where:
- Agents subscribe to channels (their name)
- Orchestrator publishes to channels
- Real-time communication between components
- Decoupled architecture

### Frontend
React web application that:
- Provides chat interface
- Shows agent dashboard
- Handles @mention autocomplete
- Displays typing indicators
- Manages WebSocket connections

---

## 💬 Getting Help

If you're stuck:

1. **Check the logs:**
   - Orchestrator terminal for routing issues
   - Agent logs for processing errors
   - Browser console for frontend issues

2. **Read the docs:**
   - Each component has its own README
   - MCP tools guide for advanced features

3. **Ask the assistant:**
   ```
   @assistant help me troubleshoot why the writer agent isn't responding
   ```

4. **Common log locations:**
   - Orchestrator: Terminal 2 output
   - Frontend: Browser Developer Console (F12)
   - Redis: Terminal 1 output

---

## ✅ Checklist: You're Ready When...

- [ ] You can open the UI and see the chat interface
- [ ] You can send messages and get responses from the assistant
- [ ] You can create a new agent via chat or dashboard
- [ ] You can start and stop agents from the dashboard
- [ ] You understand how @mentions work
- [ ] You understand conversation locking
- [ ] You can have multiple agents respond to one message
- [ ] You know where to find logs when troubleshooting

---

## 🎉 Congratulations!

You now have a working multi-agent AI system! You can:
- Chat with AI agents
- Create custom agents with specialized skills
- Have agents collaborate on tasks
- Manage agents through a web interface

**What makes this powerful:**
- Multiple specialized AI assistants instead of one general-purpose bot
- Natural conversation flow with @mentions
- Extensible architecture for adding new agents
- Optional tool integration for advanced use cases

Enjoy exploring the system, and don't hesitate to experiment with creating new agents and use cases!

---

**Questions or issues?** Check the main [README.md](README.md) or the troubleshooting section above.
