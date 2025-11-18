import { useEffect, useState, useRef } from "react";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { getAgentTheme } from "@/lib/agentTheme";
import { getApiUrl, getWsUrl } from "@/config/api";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface Agent {
  id: string;
  name: string;
  status: 'running' | 'stopped';
  pid: number | null;
}

export function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [activeAgent, setActiveAgent] = useState("assistant"); // Track which agent we're talking to
  const [availableAgents, setAvailableAgents] = useState<string[]>([]); // For autocomplete
  const [showAutocomplete, setShowAutocomplete] = useState(false);
  const [autocompleteOptions, setAutocompleteOptions] = useState<string[]>([]);
  const [selectedAutocompleteIndex, setSelectedAutocompleteIndex] = useState(0); // Track selected option
  const [typingAgents, setTypingAgents] = useState<Set<string>>(new Set()); // Track which agents are typing
  const typingTimeouts = useRef<Map<string, NodeJS.Timeout>>(new Map()); // Track typing indicator timeouts
  const ws = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const sessionId = "main";
  const [conversationCleared, setConversationCleared] = useState(false);

  // Check if orchestrator restarted and clear conversation FIRST (before loading)
  useEffect(() => {
    const checkOrchestratorRestart = async () => {
      try {
        const response = await fetch(getApiUrl('/startup_time'));
        const data = await response.json();
        const currentStartupTime = data.startup_time;

        const lastKnownStartupTime = localStorage.getItem('orchestrator_startup_time');

        if (lastKnownStartupTime && parseFloat(lastKnownStartupTime) !== currentStartupTime) {
          // Orchestrator restarted - clear conversation
          console.log('🔄 Orchestrator restarted - clearing conversation history');
          localStorage.removeItem(`chat_messages_${sessionId}`);
          setMessages([]);
          setActiveAgent('assistant'); // Reset to assistant
        }

        // Store current startup time
        localStorage.setItem('orchestrator_startup_time', currentStartupTime.toString());
        setConversationCleared(true); // Mark as checked
      } catch (err) {
        console.error('Error checking orchestrator startup time:', err);
        setConversationCleared(true); // Still allow loading
      }
    };

    checkOrchestratorRestart();
  }, [sessionId]);

  // Save active agent to localStorage whenever it changes (for dashboard highlighting)
  useEffect(() => {
    localStorage.setItem('active_agent', activeAgent);
  }, [activeAgent]);

  // Load messages from localStorage ONLY after checking for restart
  useEffect(() => {
    if (!conversationCleared) return; // Wait for restart check

    const conversationKey = `chat_messages_${sessionId}`;
    const savedMessages = localStorage.getItem(conversationKey);
    if (savedMessages) {
      try {
        const parsedMessages = JSON.parse(savedMessages);
        setMessages(parsedMessages);
        console.log(`📚 Restored ${parsedMessages.length} messages`);
      } catch (err) {
        console.error('Error loading saved messages:', err);
      }
    }
  }, [sessionId, conversationCleared]);

  // Fetch available agents for autocomplete
  useEffect(() => {
    const fetchAgents = async () => {
      try {
        const response = await fetch(getApiUrl('/agents/available'));
        const agents = await response.json();
        setAvailableAgents(agents);
      } catch (err) {
        console.error('Error fetching available agents:', err);
      }
    };

    fetchAgents();
    const interval = setInterval(fetchAgents, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  // Save messages to localStorage whenever messages change
  useEffect(() => {
    const conversationKey = `chat_messages_${sessionId}`;
    if (messages.length > 0) {
      localStorage.setItem(conversationKey, JSON.stringify(messages));
    }
  }, [messages, sessionId]);

  // Reset selected autocomplete index when options change
  useEffect(() => {
    setSelectedAutocompleteIndex(0);
  }, [autocompleteOptions]);

  useEffect(() => {
    const connectWebSocket = () => {
      const wsUrl = getWsUrl(`/ws/${sessionId}`);
      console.log("🔌 Attempting WebSocket connection to:", wsUrl);

      // Initialize WebSocket connection (no agent parameter - unified chat)
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        console.log("✅ WebSocket connection established to:", wsUrl);
        console.log("💬 Unified chat mode with @mention routing enabled");
        // No context restoration needed - conversation persistence handles this
      };

      ws.current.onmessage = (event) => {
        const chunk = event.data as string;
        console.log("📥 WebSocket received:", chunk);

        if (chunk.startsWith("[SYSTEM]")) {
          console.log(chunk);
          return;
        }

        if (chunk === "[EOS]") {
          return;
        }

        // Detect which agent sent the message and remove from typing indicators
        // Format: "[AgentName]: message" or just "message" for assistant
        const agentMatch = chunk.match(/^\[(\w+)\]:/);
        if (agentMatch) {
          const agentName = agentMatch[1].toLowerCase();
          // Clear any pending timeout for this agent
          const timeout = typingTimeouts.current.get(agentName);
          if (timeout) {
            clearTimeout(timeout);
            typingTimeouts.current.delete(agentName);
          }
          // Remove from typing indicators
          setTypingAgents(prev => {
            const next = new Set(prev);
            next.delete(agentName);
            return next;
          });
        } else {
          // Assume assistant if no prefix
          const timeout = typingTimeouts.current.get("assistant");
          if (timeout) {
            clearTimeout(timeout);
            typingTimeouts.current.delete("assistant");
          }
          setTypingAgents(prev => {
            const next = new Set(prev);
            next.delete("assistant");
            return next;
          });
        }

        // Check if this message contains @mentions (agent-to-agent delegation)
        // Use email-aware regex to prevent email addresses from triggering typing indicators
        const mentionPattern = /(?<!\w)@(\w+)(?!\.)/g;
        const mentionMatches = chunk.matchAll(mentionPattern);
        const extractedMentions = Array.from(mentionMatches, m => m[1].toLowerCase());

        // Only show typing for agents that actually exist
        const validMentions = extractedMentions.filter(mention =>
          availableAgents.some(agent => agent.toLowerCase() === mention)
        );

        if (validMentions.length > 0) {
          console.log(`🤝 Agent mentioned ${validMentions.join(', ')}, adding typing indicators`);
          setTypingAgents(prev => new Set([...prev, ...validMentions]));
        }

        // Create a new assistant message for each incoming message
        setMessages((prevMessages) => {
          const trimmedChunk = chunk.trim();
          console.log("📝 Processing message:", trimmedChunk, "Length:", trimmedChunk.length);

          // Skip empty chunks
          if (trimmedChunk === "" || trimmedChunk === "🤖") {
            console.log("❌ Filtered: empty or robot emoji");
            return prevMessages;
          }

          // Check if chunk contains only emoji characters (but NOT digits or letters)
          // Only filter if it's purely emoji like 🤖 or 👍, not "2" or "ok"
          const emojiRegex = /^[\p{Emoji}\p{Emoji_Modifier}\p{Emoji_Component}]+$/u;
          const hasAlphanumeric = /[a-zA-Z0-9]/.test(trimmedChunk);

          if (!hasAlphanumeric && emojiRegex.test(trimmedChunk)) {
            console.log("❌ Filtered: emoji only (no alphanumeric)");
            return prevMessages;
          }

          // Create a new assistant message
          console.log("✅ Adding message to chat");
          const newMessage: Message = { role: "assistant", content: chunk };
          return [...prevMessages, newMessage];
        });
      };

      ws.current.onclose = () => {
        console.log("WebSocket connection closed");
      };

      ws.current.onerror = (err) => {
        console.error("❌ WebSocket error:", err);
        console.error("🔗 Failed to connect to:", getWsUrl(`/ws/${sessionId}`));
        ws.current?.close();
      };
    };

    connectWebSocket();

    return () => {
      console.log("🧹 Cleanup: Closing WebSocket");
      if (ws.current) {
        ws.current.close();
        ws.current = null;
      }
    };
  }, [sessionId]);

  useEffect(() => {
    // Small delay to ensure DOM has updated before scrolling
    const scrollTimer = setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }, 50);

    return () => clearTimeout(scrollTimer);
  }, [messages, typingAgents]);

  // Handle input change to detect @ for autocomplete
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setInput(value);

    // Check if user is typing @ mention
    const lastAtIndex = value.lastIndexOf('@');
    if (lastAtIndex !== -1) {
      const textAfterAt = value.substring(lastAtIndex + 1);
      const hasSpaceAfter = textAfterAt.includes(' ');

      if (!hasSpaceAfter) {
        // Show autocomplete
        const matches = availableAgents.filter(agent =>
          agent.toLowerCase().startsWith(textAfterAt.toLowerCase())
        );
        if (matches.length > 0) {
          setAutocompleteOptions(matches);
          setShowAutocomplete(true);
        } else {
          setShowAutocomplete(false);
        }
      } else {
        setShowAutocomplete(false);
      }
    } else {
      setShowAutocomplete(false);
    }
  };

  // Handle autocomplete selection
  const selectAutocomplete = (agent: string) => {
    const lastAtIndex = input.lastIndexOf('@');
    const beforeAt = input.substring(0, lastAtIndex);
    setInput(`${beforeAt}@${agent} `);
    setShowAutocomplete(false);
    setSelectedAutocompleteIndex(0); // Reset selection
  };

  // Handle keyboard navigation for autocomplete
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (showAutocomplete && autocompleteOptions.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedAutocompleteIndex((prev) =>
          prev < autocompleteOptions.length - 1 ? prev + 1 : prev
        );
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedAutocompleteIndex((prev) => (prev > 0 ? prev - 1 : prev));
      } else if (e.key === 'Tab' || e.key === 'Enter') {
        if (showAutocomplete) {
          e.preventDefault();
          selectAutocomplete(autocompleteOptions[selectedAutocompleteIndex]);
        }
      } else if (e.key === 'Escape') {
        e.preventDefault();
        setShowAutocomplete(false);
      }
    } else if (e.key === 'Enter' && !showAutocomplete) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleSendMessage = async () => {
    if (input.trim() && ws.current?.readyState === WebSocket.OPEN) {
      // Extract @mentions using email-aware regex (matches backend pattern)
      // Pattern (?<!\w)@(\w+)(?!\.) prevents matching email addresses like john@example.com
      const mentionPattern = /(?<!\w)@(\w+)(?!\.)/g;
      const mentionMatches = input.matchAll(mentionPattern);
      const extractedMentions = Array.from(mentionMatches, m => m[1].toLowerCase());

      // Filter to only include agents that actually exist
      const mentionedAgents = extractedMentions.filter(mention =>
        availableAgents.some(agent => agent.toLowerCase() === mention)
      );

      // Smart routing logic (matches backend):
      // - If first mention is "assistant" -> delegation mode (only assistant)
      // - If multiple mentions (not starting with assistant) -> parallel broadcast (all agents)
      // - If single mention (not assistant) -> route to that agent and lock
      // - If no mentions -> use active agent or assistant
      const firstMention = mentionedAgents.length > 0 ? mentionedAgents[0] : null;
      const isDelegationMode = firstMention === "assistant";
      const isParallelBroadcast = mentionedAgents.length > 1 && !isDelegationMode;

      // Determine which agents to show typing for
      let agentsToShowTyping: string[];
      if (isDelegationMode) {
        // Delegation mode: only assistant is typing initially
        agentsToShowTyping = ["assistant"];
      } else if (isParallelBroadcast) {
        // Parallel broadcast: all mentioned agents
        agentsToShowTyping = mentionedAgents;
      } else {
        // Single agent mention or default (no mentions)
        agentsToShowTyping = firstMention ? [firstMention] : [activeAgent !== "assistant" ? activeAgent : "assistant"];
      }

      // Add agents to typing indicators with 500ms delay
      // This allows the user's message to render first before showing typing
      // Short enough to feel responsive, long enough to avoid visual glitches
      agentsToShowTyping.forEach(agentName => {
        // Clear any existing timeout for this agent
        const existingTimeout = typingTimeouts.current.get(agentName);
        if (existingTimeout) {
          clearTimeout(existingTimeout);
        }

        // Set new timeout to show typing after 500ms
        const timeout = setTimeout(() => {
          setTypingAgents(prev => new Set([...prev, agentName]));
          typingTimeouts.current.delete(agentName);
        }, 500);

        typingTimeouts.current.set(agentName, timeout);
      });

      // For auto-start logic (only check first mentioned agent)
      const targetAgent = firstMention || (activeAgent !== "assistant" ? activeAgent : null);

      // Auto-start agent if mentioned and not running
      if (targetAgent && targetAgent !== "assistant") {
        try {
          const statusResponse = await fetch(getApiUrl('/agents'));
          const allAgents = await statusResponse.json();
          const agent = allAgents.find((a: Agent) => a.name === targetAgent);

          if (!agent || agent.status !== 'running') {
            console.log(`🚀 Auto-starting ${targetAgent}...`);
            const startResponse = await fetch(getApiUrl('/agents/start'), {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ name: targetAgent })
            });
            const result = await startResponse.json();
            if (result.ok) {
              console.log(`✅ ${targetAgent} start request sent, waiting for agent to be ready...`);

              // Poll agent status until it's actually running (max 5 seconds)
              let attempts = 0;
              const maxAttempts = 10;
              while (attempts < maxAttempts) {
                await new Promise(resolve => setTimeout(resolve, 500));
                const checkResponse = await fetch(getApiUrl('/agents'));
                const agents = await checkResponse.json();
                const runningAgent = agents.find((a: Agent) => a.name === targetAgent && a.status === 'running');

                if (runningAgent) {
                  console.log(`✅ ${targetAgent} is now running and ready!`);
                  // Extra 500ms to ensure WebSocket connections are established
                  await new Promise(resolve => setTimeout(resolve, 500));
                  break;
                }
                attempts++;
              }

              if (attempts >= maxAttempts) {
                console.warn(`⚠️ ${targetAgent} took too long to start, sending message anyway...`);
              }
            } else {
              console.error(`Failed to start ${targetAgent}:`, result.error);
            }
          }
        } catch (err) {
          console.error('Error auto-starting agent:', err);
        }
      }

      if (firstMention) {
        // Only lock agent if it's a single agent or delegation mode
        // Don't lock for parallel broadcast (multiple agents, not starting with assistant)
        if (!isParallelBroadcast) {
          console.log(`🔄 Switching to agent: ${firstMention}`);
          setActiveAgent(firstMention);
        } else {
          // Parallel broadcast: unlock if currently locked to an agent
          console.log(`📢 Parallel broadcast to ${mentionedAgents.length} agents - clearing lock`);
          setActiveAgent('assistant');
        }

        // Send the message as-is (with @mentions)
        ws.current.send(input);
        setMessages(prev => [...prev, { role: 'user', content: input }]);

        if (isDelegationMode) {
          console.log(`💬 Delegation mode: assistant will coordinate with others`);
        } else if (isParallelBroadcast) {
          console.log(`💬 Parallel broadcast to: ${mentionedAgents.join(', ')}`);
        } else {
          console.log(`💬 Sending to ${firstMention}`);
        }
      } else {
        // No @mention - use active agent
        let messageToSend = input;
        if (activeAgent !== "assistant") {
          // Prefix with @mention for non-assistant agents
          messageToSend = `@${activeAgent} ${input}`;
          console.log(`💬 Sending to ${activeAgent}: ${input}`);
        }
        ws.current.send(messageToSend);
        setMessages(prev => [...prev, { role: 'user', content: input }]);
      }
      setInput("");
    }
  };

  // Function to clear conversation history
  const clearConversation = async () => {
    const conversationKey = `chat_messages_${sessionId}`;
    setMessages([]);
    localStorage.removeItem(conversationKey);

    // Also clear backend chat history
    try {
      const response = await fetch(getApiUrl(`/chat/${sessionId}/clear`), {
        method: 'POST'
      });
      if (response.ok) {
        const result = await response.json();
        console.log("🗑️ Conversation history cleared:", result.message);
      }
    } catch (err) {
      console.log("⚠️ Could not clear backend chat history:", err);
    }

    console.log(`🗑️ Conversation history cleared`);
  };

  return (
    <Card className="w-full h-full flex flex-col shadow-xl border-2 border-gray-200 dark:border-gray-700 animate-fade-in">
      <CardHeader className="bg-gradient-to-r from-slate-700 to-slate-800 text-white border-b-0 rounded-t-lg">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center">
              <span className="text-2xl">💬</span>
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">
                AI Agent Chat
              </h1>
              <p className="text-slate-200 text-sm">
                Multi-agent conversations with @mentions
              </p>
            </div>
          </div>
          <Button
            onClick={clearConversation}
            variant="outline"
            size="sm"
            className="bg-white/10 hover:bg-white/20 text-white border-white/30 hover:border-white/50"
            title="Clear conversation history"
          >
            🗑️ Clear Chat
          </Button>
        </div>
      </CardHeader>
      <CardContent className="flex-grow overflow-auto p-6 space-y-6">
        {messages.map((msg, index) => {
          // Detect which agent sent the message by checking for [AgentName]: prefix
          let agentName = 'assistant';
          let displayContent = msg.content;
          if (msg.role === 'assistant' && msg.content.startsWith('[')) {
            const match = msg.content.match(/^\[(\w+)\]:\s*/);
            if (match) {
              agentName = match[1].toLowerCase();
              displayContent = msg.content.substring(match[0].length);
            }
          }
          const theme = getAgentTheme(agentName);

          return (
            <div key={index} className={`flex items-start gap-4 animate-slide-up ${msg.role === 'user' ? 'justify-end' : ''}`}>
              {msg.role === 'assistant' && (
                <div className={`w-10 h-10 rounded-full bg-gradient-to-br ${theme.bgGradient} flex items-center justify-center flex-shrink-0 shadow-md`}>
                  {agentName === 'assistant' ? (
                    <span className="text-lg">{theme.icon}</span>
                  ) : (
                    <span className="text-white font-bold text-lg uppercase">
                      {agentName.charAt(0)}
                    </span>
                  )}
                </div>
              )}
              <div className={`rounded-2xl px-5 py-3 shadow-lg max-w-[80%] transition-all duration-200 hover:shadow-xl ${
                msg.role === 'user'
                  ? 'gradient-primary text-primary-foreground ml-auto'
                  : `bg-card border-2 ${theme.borderColor} border-opacity-50`
              }`}>
                {msg.role === 'user' ? (
                  <p className="text-sm font-medium">{msg.content}</p>
                ) : (
                  <div className="text-sm prose prose-sm max-w-none dark:prose-invert">
                    <div className="whitespace-pre-wrap font-mono text-sm leading-relaxed">
                      {displayContent}
                    </div>
                  </div>
                )}
              </div>
              {msg.role === 'user' && (
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-green-500 to-blue-600 flex items-center justify-center flex-shrink-0">
                  <span className="text-sm">👤</span>
                </div>
              )}
            </div>
          );
        })}

        {/* Typing indicators */}
        {Array.from(typingAgents).map((agentName) => {
          const theme = getAgentTheme(agentName);
          return (
            <div key={`typing-${agentName}`} className="flex items-start gap-4 animate-slide-up">
              <div className={`w-10 h-10 rounded-full bg-gradient-to-br ${theme.bgGradient} flex items-center justify-center flex-shrink-0 shadow-md`}>
                {agentName === 'assistant' ? (
                  <span className="text-lg">{theme.icon}</span>
                ) : (
                  <span className="text-white font-bold text-lg uppercase">
                    {agentName.charAt(0)}
                  </span>
                )}
              </div>
              <div className={`rounded-2xl px-5 py-3 shadow-lg transition-all duration-200 bg-card border-2 ${theme.borderColor} border-opacity-50`}>
                <div className="flex items-center gap-2">
                  <div className="flex gap-1">
                    <div className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '0ms' }}></div>
                    <div className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '150ms' }}></div>
                    <div className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '300ms' }}></div>
                  </div>
                  <span className="text-xs text-muted-foreground ml-1">{agentName} is typing...</span>
                </div>
              </div>
            </div>
          );
        })}

        <div ref={messagesEndRef} />
      </CardContent>
      <CardFooter className="p-6 border-t bg-gray-50 dark:bg-gray-800 rounded-b-lg">
        <div className="flex flex-col w-full space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border-2 ${
                activeAgent === 'assistant'
                  ? 'bg-slate-50 dark:bg-slate-800 border-slate-300 dark:border-slate-600'
                  : `bg-gradient-to-r ${getAgentTheme(activeAgent).bgGradient} border-transparent`
              } transition-all`}>
                <span className={`text-lg ${activeAgent !== 'assistant' ? '' : ''}`}>
                  {getAgentTheme(activeAgent).icon}
                </span>
                <span className={`font-bold text-sm ${
                  activeAgent === 'assistant'
                    ? 'text-slate-700 dark:text-slate-200'
                    : 'text-white'
                }`}>
                  {activeAgent}
                </span>
              </div>
              {activeAgent !== 'assistant' && (
                <button
                  onClick={() => setActiveAgent('assistant')}
                  className="px-2 py-1 text-xs bg-slate-200 hover:bg-slate-300 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 rounded-md transition-colors font-medium"
                  title="Switch back to assistant"
                >
                  Unlock
                </button>
              )}
            </div>
            <div className="text-xs text-muted-foreground">
              Type <code className="bg-muted px-1 rounded">@</code> to mention agents
            </div>
          </div>
          <div className="relative flex w-full items-center space-x-3">
            {/* Autocomplete dropdown */}
            {showAutocomplete && autocompleteOptions.length > 0 && (
              <div className="absolute bottom-full mb-2 left-0 bg-white dark:bg-gray-800 border-2 border-blue-400 rounded-lg shadow-xl z-20 min-w-[200px]">
                <div className="p-2">
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-1 px-2">Available agents (↑↓ Tab/Enter):</div>
                  {autocompleteOptions.map((agent, index) => (
                    <button
                      key={agent}
                      onClick={() => selectAutocomplete(agent)}
                      className={`w-full text-left px-3 py-2 rounded flex items-center gap-2 transition-colors ${
                        index === selectedAutocompleteIndex
                          ? 'bg-blue-500 text-white font-bold'
                          : 'hover:bg-blue-100 dark:hover:bg-blue-900'
                      }`}
                    >
                      <span className="text-lg">🤖</span>
                      <span className="font-medium">@{agent}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            <Input
              id="message"
              name="message"
              placeholder={activeAgent === 'assistant'
                ? "Type your message... (type @ for agents)"
                : `Message for ${activeAgent}... (auto-prefixed with @${activeAgent})`}
              className={`flex-1 h-12 rounded-xl border-2 transition-colors font-medium ${
                activeAgent === 'assistant'
                  ? 'border-gray-300 dark:border-gray-600 focus:border-blue-500'
                  : `${getAgentTheme(activeAgent).borderColor} border-opacity-70 focus:${getAgentTheme(activeAgent).borderColor} focus:border-opacity-100`
              }`}
              autoComplete="off"
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
            />
            <Button
              onClick={handleSendMessage}
              className="h-12 px-6 rounded-xl bg-blue-600 hover:bg-blue-700 text-white shadow-lg hover:shadow-xl transition-all duration-200 font-semibold"
              disabled={!input.trim()}
            >
              <span className="mr-2">Send</span>
              <span>🚀</span>
            </Button>
          </div>
        </div>
      </CardFooter>
    </Card>
  );
}
