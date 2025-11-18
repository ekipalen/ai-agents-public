# Frontend - AI Agents Chat UI

Modern React + TypeScript chat interface for the AI Agents multi-agent system. Built with Vite for fast development and optimized production builds.

## Features

- **💬 Real-time Chat** - WebSocket-powered instant messaging
- **🎯 @Mention System** - Autocomplete for agent mentions with ↑↓ Tab/Enter navigation
- **🔒 Conversation Locking** - Visual indicator for locked conversations
- **🤖 Agent Dashboard** - View, create, start, stop, and delete agents
- **⌨️ Typing Indicators** - See when agents are processing
- **🎨 Agent Themes** - Each agent has unique colors and icons
- **📜 Auto-scroll** - Smart scrolling with user override
- **📝 Message History** - Persistent conversation history

## Technology Stack

- **React 19** - UI library
- **TypeScript** - Type-safe development
- **Vite** - Build tool and dev server
- **TailwindCSS** - Utility-first styling
- **Lucide Icons** - Icon library
- **WebSocket** - Real-time communication

## Directory Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── Chat.tsx          # Main chat interface
│   │   ├── Dashboard.tsx     # Agent management
│   │   ├── AgentCreator.tsx  # Create agent modal
│   │   └── TypingIndicator.tsx
│   ├── App.tsx               # Root component
│   ├── main.tsx             # Entry point
│   └── index.css            # Global styles
├── public/                  # Static assets
├── package.json
└── vite.config.ts
```

## Installation

```bash
cd frontend
npm install
```

## Development

```bash
npm run dev
```

Access at `http://localhost:5173`

The dev server features:
- **Hot Module Replacement (HMR)** - Instant updates without page refresh
- **TypeScript checking** - Type errors in console
- **Fast refresh** - Preserve component state on edits

## Production Build

```bash
npm run build
npm run preview
```

Optimized build output in `dist/`:
- Minified JavaScript bundles
- Optimized CSS
- Code splitting for faster loads
- Tree-shaking to remove unused code

## Key Components

### Chat.tsx

Main chat interface component.

**Features:**
- WebSocket connection management
- @mention autocomplete with keyboard navigation
- Message rendering with agent themes
- Typing indicators
- Conversation locking UI
- Auto-scroll with user override

**State Management:**
```typescript
const [messages, setMessages] = useState<Message[]>([])
const [input, setInput] = useState('')
const [lockedAgent, setLockedAgent] = useState<string | null>(null)
const [mentionSuggestions, setMentionSuggestions] = useState<Agent[]>([])
```

**WebSocket Events:**
- `message` - Incoming chat messages
- `agent_typing` - Agent started typing
- `agent_stopped_typing` - Agent finished
- `agent_status` - Agent started/stopped
- `conversation_locked` - Agent locked
- `conversation_unlocked` - Agent unlocked

### Dashboard.tsx

Agent management interface.

**Features:**
- Agent list with status (running/stopped)
- Create new agents
- Start/stop agents
- Delete agents
- Real-time status updates via WebSocket

**Agent Operations:**
```typescript
const startAgent = (name: string) => {
  fetch(`${API_URL}/agents/start`, {
    method: 'POST',
    body: JSON.stringify({ name })
  })
}
```

### AgentCreator.tsx

Modal for creating new agents.

**Features:**
- Name and role input
- Dynamic capability list (add/remove)
- Form validation
- Error handling

## Styling

Uses **TailwindCSS** with custom configuration:

```typescript
// tailwind.config.js
theme: {
  extend: {
    colors: {
      // Custom agent colors
      'agent-blue': '#3b82f6',
      'agent-green': '#10b981',
      // ...
    }
  }
}
```

**Agent Themes:**
Each agent gets a unique color from a predefined palette:
```typescript
const agentColors = [
  'bg-blue-500', 'bg-green-500', 'bg-purple-500',
  'bg-pink-500', 'bg-orange-500', 'bg-cyan-500'
]
```

## @Mention Autocomplete

**Trigger:** Type `@` to show agent suggestions

**Navigation:**
- `↑` / `↓` - Navigate suggestions
- `Tab` / `Enter` - Select agent
- `Esc` - Close suggestions
- Continue typing to filter

**Implementation:**
```typescript
const handleInputChange = (e) => {
  const value = e.target.value
  const cursorPos = e.target.selectionStart
  
  // Detect @ mention
  const beforeCursor = value.slice(0, cursorPos)
  const match = beforeCursor.match(/@(\w*)$/)
  
  if (match) {
    const query = match[1].toLowerCase()
    const filtered = agents.filter(a => 
      a.name.toLowerCase().includes(query)
    )
    setMentionSuggestions(filtered)
  }
}
```

## WebSocket Communication

**Connection:**
```typescript
const ws = new WebSocket(`ws://localhost:9000/ws/${sessionId}`)

ws.onmessage = (event) => {
  const data = JSON.parse(event.data)
  
  switch(data.type) {
    case 'message':
      setMessages(prev => [...prev, data.message])
      break
    case 'agent_typing':
      setTypingAgents(prev => [...prev, data.agent])
      break
    // ...
  }
}
```

**Sending Messages:**
```typescript
const sendMessage = (content: string) => {
  ws.send(JSON.stringify({
    type: 'chat',
    content,
    session_id: sessionId
  }))
}
```

## Environment Variables

Create `.env` in project root (not frontend/):

```bash
VITE_API_URL=http://localhost:9000
VITE_WS_URL=ws://localhost:9000
```

Access in code:
```typescript
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:9000'
```

## TypeScript

**Type Definitions:**
```typescript
interface Message {
  id: string
  content: string
  sender: string
  timestamp: number
  isUser: boolean
}

interface Agent {
  name: string
  role: string
  status: 'running' | 'stopped'
  capabilities: Capability[]
}

interface Capability {
  name: string
  description: string
}
```

**Type Checking:**
```bash
npm run typecheck  # Check types without building
```

## Testing

```bash
npm run test       # Run tests (if configured)
npm run lint       # ESLint
```

## Performance Optimization

**Code Splitting:**
- React Router lazy loading
- Dynamic imports for large components

**Memoization:**
```typescript
const MemoizedMessage = React.memo(MessageComponent)
```

**Virtual Scrolling:**
For long message lists, consider adding:
- `react-window` or `react-virtualized`
- Only render visible messages
- Dramatically improves performance with 1000+ messages

## Accessibility

- **Keyboard Navigation** - Full keyboard support for @mentions
- **ARIA Labels** - Screen reader support
- **Focus Management** - Proper focus handling in modals
- **Color Contrast** - WCAG AA compliant colors

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

## Development Tips

**Hot Reload Issues?**
```bash
rm -rf node_modules .vite
npm install
npm run dev
```

**WebSocket Not Connecting?**
- Check orchestrator is running on port 9000
- Verify `VITE_WS_URL` in `.env`
- Check browser console for errors

**Type Errors?**
```bash
npm run typecheck
```

**Styling Issues?**
```bash
# Rebuild Tailwind
npm run dev
# Tailwind rebuilds automatically
```

## Contributing

When adding new features:
1. Add TypeScript types in component files
2. Update this README with new features
3. Test on multiple browsers
4. Ensure keyboard accessibility
5. Add loading states for async operations

## See Also

- [Main README](../README.md) - Project overview
- [Orchestrator README](../orchestrator/README.md) - Backend API
- [MCP_TOOLS_GUIDE.md](../MCP_TOOLS_GUIDE.md) - Tool integration
