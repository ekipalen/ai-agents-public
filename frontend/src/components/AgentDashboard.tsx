import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from './ui/button';
import { RunbookTooltip } from './RunbookTooltip';
import { RunbookModal } from './RunbookModal';
import { getAgentTheme } from '@/lib/agentTheme';
import { getApiUrl } from '@/config/api';

interface RunningAgent {
    id: string;
    name: string;
    role: string;
    status: 'running' | 'stopped';
    pid: number | null;
}

interface DisplayAgent {
    id: string;
    name: string;
    status: 'running' | 'stopped';
    pid: number | null;
}

interface AgentFlash {
    [agentName: string]: boolean; // true if agent should flash
}

interface AgentRunbook {
    agent_name: string;
    role: string;
    job_title?: string;
    capabilities: Array<{
        name: string;
        description: string;
    }>;
    collaboration_patterns: string[];
    dependencies: string[];
    version: string;
}

export function AgentDashboard() {
    const [runningAgents, setRunningAgents] = useState<RunningAgent[]>([]);
    const [availableAgents, setAvailableAgents] = useState<string[]>([]);
    const [displayAgents, setDisplayAgents] = useState<DisplayAgent[]>([]);
    const [agentRunbooks, setAgentRunbooks] = useState<AgentRunbook[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [modalAgent, setModalAgent] = useState<string | null>(null);  // Renamed to avoid conflict with prop
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [agentFlash, setAgentFlash] = useState<AgentFlash>({});
    const [activeAgent, setActiveAgent] = useState<string>('assistant'); // Track which agent is active in chat

    // Helper function to shorten description for UI display
    const shortenDescription = (description: string, maxLength: number = 80): string => {
        if (description.length <= maxLength) return description;
        
        // Try to break at a sentence boundary first
        const sentences = description.split('. ');
        if (sentences[0].length <= maxLength) {
            return sentences[0] + (sentences.length > 1 ? '.' : '');
        }
        
        // Otherwise truncate at word boundary
        const words = description.split(' ');
        let result = '';
        for (const word of words) {
            if ((result + ' ' + word).length > maxLength - 3) break;
            result += (result ? ' ' : '') + word;
        }
        return result + '...';
    };

    // Dynamic agent display info based on backend data
    const getAgentDisplayInfo = (agentName: string) => {
        // First try to get info from runbooks data (preferred source for job titles)
        const runbook = agentRunbooks.find(r => r.agent_name.toLowerCase() === agentName.toLowerCase());
        if (runbook) {
            return {
                displayName: agentName.charAt(0).toUpperCase() + agentName.slice(1),
                description: runbook.job_title || runbook.role || 'AI Agent'
            };
        }
        
        // Fallback to running agents data
        const runningAgent = runningAgents.find(a => a.name.toLowerCase() === agentName.toLowerCase());
        if (runningAgent && runningAgent.role) {
            return {
                displayName: agentName.charAt(0).toUpperCase() + agentName.slice(1),
                description: shortenDescription(runningAgent.role)
            };
        }
        
        // Final fallback
        return {
            displayName: agentName.charAt(0).toUpperCase() + agentName.slice(1),
            description: 'AI Agent'
        };
    };

    const fetchAgents = async () => {
        try {
            const [runningRes, availableRes, runbooksRes] = await Promise.all([
                fetch(getApiUrl('/agents')),
                fetch(getApiUrl('/agents/available')),
                fetch(getApiUrl('/agents/runbooks'))
            ]);
            
            if (!runningRes.ok) throw new Error('Failed to fetch running agents');
            if (!availableRes.ok) throw new Error('Failed to fetch available agents');

            const runningData = await runningRes.json();
            const availableData = await availableRes.json();
            
            setRunningAgents(runningData);
            setAvailableAgents(availableData);

            // Handle runbooks - may not be available in all deployments
            if (runbooksRes.ok) {
                const runbooksData = await runbooksRes.json();
                setAgentRunbooks(runbooksData);
                // Removed spammy log - was called every second
                // console.log(`📚 Loaded ${runbooksData.length} agent runbooks from backend`);
            } else {
                // Removed spammy log - was called every second
                // console.log('⚠️ Runbooks endpoint not available, using fallback descriptions');
                setAgentRunbooks([]);
            }

        } catch (err) {
            setError(err instanceof Error ? err.message : 'An unknown error occurred');
        }
    };

    useEffect(() => {
        fetchAgents();
        const interval = setInterval(fetchAgents, 2000); // Refresh every 2 seconds
        return () => clearInterval(interval);
    }, []);

    // Poll localStorage for active agent (updated by Chat component)
    useEffect(() => {
        const checkActiveAgent = () => {
            const active = localStorage.getItem('active_agent') || 'assistant';
            setActiveAgent(active);
        };

        checkActiveAgent(); // Initial check
        const interval = setInterval(checkActiveAgent, 500); // Check every 500ms
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        const allAgentNames = new Set([...availableAgents, ...runningAgents.map(a => a.name)]);

        const mergedAgents = Array.from(allAgentNames).map(name => {
            const runningAgent = runningAgents.find(a => a.name === name);
            if (runningAgent && runningAgent.status === 'running') {
                return {
                    id: runningAgent.id,
                    name: runningAgent.name,
                    status: runningAgent.status,
                    pid: runningAgent.pid,
                };
            }
            return {
                id: name, // Use name as a fallback ID for non-running agents
                name: name,
                status: 'stopped' as const,
                pid: null, // Always null for stopped agents
            };
        });

        // Sort agents: Assistant first, then running agents alphabetically, then stopped agents alphabetically
        const sortedAgents = mergedAgents.sort((a, b) => {
            // Assistant always comes first
            if (a.name === 'assistant') return -1;
            if (b.name === 'assistant') return 1;
            
            // If status is different, running agents come before stopped agents
            if (a.status !== b.status) {
                if (a.status === 'running') return -1;
                if (b.status === 'running') return 1;
            }
            
            // Within the same status group, sort alphabetically
            return a.name.localeCompare(b.name);
        });
        
        setDisplayAgents(sortedAgents);
    }, [runningAgents, availableAgents]);

    // Simple flash notification function
    const flashAgent = (agentName: string) => {
        // console.log(`⚡ Flashing ${agentName}`);
        setAgentFlash(prev => ({ ...prev, [agentName]: true }));
        // Auto-remove flash after animation completes
        setTimeout(() => {
            setAgentFlash(prev => ({ ...prev, [agentName]: false }));
        }, 1000);
    };

    // Helper function to add new agent display info
    const addAgentDisplayInfo = (agentName: string, displayName: string, description: string) => {
        // console.log(`📝 Adding agent display info: ${agentName} -> ${displayName} (${description})`);

        // Update local runbooks state with new agent info
        setAgentRunbooks(prev => {
            const existing = prev.find(r => r.agent_name.toLowerCase() === agentName.toLowerCase());
            if (existing) {
                // Update existing runbook
                return prev.map(r =>
                    r.agent_name.toLowerCase() === agentName.toLowerCase()
                        ? { ...r, job_title: shortenDescription(description, 50), role: description }
                        : r
                );
            } else {
                // Add new runbook entry
                return [...prev, {
                    agent_name: agentName,
                    role: description,
                    job_title: shortenDescription(description, 50),
                    capabilities: [{ name: displayName, description: description }],
                    collaboration_patterns: [],
                    dependencies: [],
                    version: "1.0"
                }];
            }
        });

        // console.log(`✅ Updated local agent info for ${agentName}`);
    };

    // Helper function to delete an agent
    const deleteAgent = async (agentName: string) => {
        setLoading(true);
        setError(null);
        try {
            console.log(`🗑️ Attempting to delete agent: ${agentName}`);

            // Call the correct backend endpoint (POST /agents/delete)
            const response = await fetch(getApiUrl('/agents/delete'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: agentName,
                    remove_runbook: true  // Also delete the runbook file
                })
            });

            const result = await response.json();

            if (!response.ok || !result.ok) {
                throw new Error(result.error || 'Failed to delete agent');
            }

            console.log(`✅ Agent ${agentName} deleted successfully`);
            await fetchAgents(); // Refresh the list
            setTimeout(fetchAgents, 1000); // Additional refresh
            
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to delete agent');
            console.error('Delete agent error:', err);
        } finally {
            setLoading(false);
        }
    };

    // Helper function for starting new agents (with auto-restart)
    const startNewAgent = async (agentName: string) => {
        console.log(`🆕 Starting NEW agent: ${agentName}`);
        await handleStart(agentName, true); // true = isNewAgent
    };

    // Simple function to get current agent data for assistant
    const getAgentData = () => {
        return {
            running: runningAgents,
            available: availableAgents,
            runbooks: agentRunbooks
        };
    };

    // Smart agent name resolver with fuzzy matching
    const resolveAgentName = (inputName: string): { found: boolean; suggestions: string[]; bestMatch?: string } => {
        const input = inputName.toLowerCase().trim();
        const runningAgentNames = runningAgents.map(a => a.name);
        const runbookAgentNames = agentRunbooks.map(a => a.agent_name);
        const agentNames = Array.from(new Set([...runningAgentNames, ...runbookAgentNames]));
        
        // Exact match first
        const exactMatch = agentNames.find(name => name.toLowerCase() === input);
        if (exactMatch) {
            return { found: true, suggestions: [exactMatch], bestMatch: exactMatch };
        }
        
        // Calculate similarity scores
        const calculateSimilarity = (str1: string, str2: string): number => {
            const s1 = str1.toLowerCase();
            const s2 = str2.toLowerCase();
            
            // Exact substring match gets high score
            if (s1.includes(s2) || s2.includes(s1)) {
                return 0.8;
            }
            
            // Levenshtein distance based similarity
            const matrix = Array(s2.length + 1).fill(null).map(() => Array(s1.length + 1).fill(null));
            
            for (let i = 0; i <= s1.length; i++) matrix[0][i] = i;
            for (let j = 0; j <= s2.length; j++) matrix[j][0] = j;
            
            for (let j = 1; j <= s2.length; j++) {
                for (let i = 1; i <= s1.length; i++) {
                    const cost = s1[i - 1] === s2[j - 1] ? 0 : 1;
                    matrix[j][i] = Math.min(
                        matrix[j][i - 1] + 1,     // deletion
                        matrix[j - 1][i] + 1,     // insertion
                        matrix[j - 1][i - 1] + cost // substitution
                    );
                }
            }
            
            const maxLen = Math.max(s1.length, s2.length);
            return 1 - (matrix[s2.length][s1.length] / maxLen);
        };
        
        // Find matches with similarity > 0.5
        const matches = agentNames.map(name => ({
            name,
            similarity: calculateSimilarity(input, name)
        }))
        .filter(match => match.similarity > 0.5)
        .sort((a, b) => b.similarity - a.similarity);
        
        if (matches.length > 0) {
            return {
                found: true,
                suggestions: matches.map(m => m.name),
                bestMatch: matches[0].name
            };
        }
        
        return { found: false, suggestions: [] };
    };

    // Smart delete function that handles typos
    const smartDeleteAgent = async (inputName: string) => {
        const resolution = resolveAgentName(inputName);
        
        if (!resolution.found) {
            console.log(`❌ No agent found matching "${inputName}"`);
            return false;
        }
        
        if (resolution.bestMatch) {
            console.log(`🔍 Resolved "${inputName}" to "${resolution.bestMatch}"`);
            await deleteAgent(resolution.bestMatch);
            return true;
        }
        
        return false;
    };

    // Smart start function that handles typos
    const smartStartAgent = async (inputName: string, isNew: boolean = false) => {
        const resolution = resolveAgentName(inputName);
        
        if (!resolution.found) {
            console.log(`❌ No agent found matching "${inputName}"`);
            return false;
        }
        
        if (resolution.bestMatch) {
            console.log(`🔍 Resolved "${inputName}" to "${resolution.bestMatch}"`);
            await handleStart(resolution.bestMatch, isNew);
            return true;
        }
        
        return false;
    };

    // Expose functions globally for external calls
    useEffect(() => {
        (window as any).flashAgent = flashAgent;
        (window as any).addAgentDisplayInfo = addAgentDisplayInfo;
        (window as any).deleteAgent = deleteAgent;
        (window as any).startNewAgent = startNewAgent;
        (window as any).getAgentData = getAgentData;
        (window as any).resolveAgentName = resolveAgentName;
        (window as any).smartDeleteAgent = smartDeleteAgent;
        (window as any).smartStartAgent = smartStartAgent;
        
        // Demo function to test flash
        (window as any).demoFlash = (agentName: string) => {
            console.log(`⚡ Demo: Flashing ${agentName}`);
            flashAgent(agentName);
        };
        
        return () => {
            delete (window as any).flashAgent;
            delete (window as any).addAgentDisplayInfo;
            delete (window as any).deleteAgent;
            delete (window as any).startNewAgent;
            delete (window as any).getAgentData;
            delete (window as any).resolveAgentName;
            delete (window as any).smartDeleteAgent;
            delete (window as any).smartStartAgent;
            delete (window as any).demoFlash;
        };
    }, [runningAgents, agentRunbooks, availableAgents]);

    const handleStop = async (agentId: string) => {
        setLoading(true);
        try {
            const response = await fetch(getApiUrl(`/agents/${agentId}/stop`), {
                method: 'POST',
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to stop agent');
            }
            await fetchAgents(); // Refresh the list immediately
            setTimeout(fetchAgents, 500); // Additional refresh after 500ms
        } catch (err) {
            setError(err instanceof Error ? err.message : 'An unknown error occurred');
        } finally {
            setLoading(false);
        }
    };
    
    const handleStart = async (agentName: string, isNewAgent: boolean = false) => {
        setLoading(true);
        setError(null);
        try {
            const response = await fetch(getApiUrl('/agents/start'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: agentName }),
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to start agent');
            }
            await fetchAgents(); // Refresh immediately

            // Only auto-restart if this is a newly created agent
            if (isNewAgent) {
                console.log(`🆕 New agent detected - will auto-restart ${agentName} for proper initialization`);
                setTimeout(async () => {
                    try {
                        console.log(`🔄 Auto-restarting NEW agent ${agentName}...`);

                        // Get the agent ID for the restart
                        const agentsResponse = await fetch(getApiUrl('/agents'));
                        if (agentsResponse.ok) {
                            const agents = await agentsResponse.json();
                            const agent = agents.find((a: RunningAgent) => a.name === agentName);

                            if (agent && agent.status === 'running') {
                                // Stop the agent
                                await fetch(getApiUrl(`/agents/${agent.id}/stop`), {
                                    method: 'POST',
                                });

                                // Wait a moment then start it again
                                setTimeout(async () => {
                                    await fetch(getApiUrl('/agents/start'), {
                                        method: 'POST',
                                        headers: { 'Content-Type': 'application/json' },
                                        body: JSON.stringify({ name: agentName }),
                                    });
                                    console.log(`✅ Auto-restart completed for NEW agent ${agentName}`);
                                    await fetchAgents();
                                }, 1000);
                            }
                        }
                    } catch (restartErr) {
                        console.log(`⚠️ Auto-restart failed for ${agentName}:`, restartErr);
                    }
                }, 2000);
            } else {
                console.log(`🔄 Starting existing agent ${agentName} - no auto-restart needed`);
            }
            
            setTimeout(fetchAgents, 500); // Additional refresh after 500ms
        } catch (err) {
             setError(err instanceof Error ? err.message : 'An unknown error occurred');
        } finally {
            setLoading(false);
        }
    };

    return (
        <>
            <Card className="w-full h-full flex flex-col shadow-xl border-2 border-gray-200 dark:border-gray-700 animate-fade-in overflow-hidden min-w-[400px]">
                <CardHeader className="bg-gradient-to-r from-slate-700 to-slate-800 text-white border-b-0 rounded-t-lg">
                    <div className="flex items-center gap-3">
                        <div className="w-12 h-12 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center">
                            <span className="text-2xl">🚀</span>
                        </div>
                        <div>
                            <CardTitle className="text-white text-2xl font-bold">
                                Agent Dashboard
                            </CardTitle>
                            <p className="text-slate-200">Manage your AI agents</p>
                        </div>
                    </div>
                </CardHeader>
                <CardContent className="flex-grow flex flex-col gap-6 p-6 min-h-0">
                     {error && (
                        <div className="bg-destructive/10 border border-destructive/20 rounded-xl p-4 animate-slide-up">
                            <p className="text-destructive text-sm font-medium">{error}</p>
                        </div>
                    )}
                    
                    <div className="flex-grow overflow-auto min-h-0 scrollbar-thin">
                        <div className="space-y-2 sm:space-y-3 pr-2">
                            {displayAgents.map((agent, index) => {
                                const agentInfo = getAgentDisplayInfo(agent.name);
                                const isAssistant = agent.name === 'assistant';
                                const isActive = agent.name === activeAgent;
                                const agentTheme = getAgentTheme(agent.name);

                                // Use pre-defined Tailwind classes for colors (not dynamic)
                                const statusDotColor = agent.status === 'running'
                                    ? `${agentTheme.dotColor} animate-pulse`
                                    : 'bg-slate-500';

                                return (
                                <div
                                    key={agent.id}
                                    className={`bg-white dark:bg-gray-800 border-2 ${agentTheme.borderColor} dark:${agentTheme.borderColor} ${
                                        isActive
                                            ? `shadow-xl shadow-${agentTheme.color}-500/40`
                                            : 'shadow-md hover:shadow-lg'
                                    } rounded-xl p-3 sm:p-5 transition-all duration-200 animate-slide-up ${
                                        agentFlash[agent.name] ? 'animate-flash' : ''
                                    }`}
                                    style={{ animationDelay: `${index * 0.1}s` }}
                                >
                                    <div className="flex items-center justify-between gap-3 sm:gap-4">
                                        <div className="flex items-center gap-3 sm:gap-4">
                                            <div className={`w-4 h-4 rounded-full border-2 shadow-lg border-white ${statusDotColor}`} />
                                            <div className="flex-grow">
                                                <RunbookTooltip agentName={agent.name}>
                                                    <span
                                                        className="font-semibold cursor-pointer transition-colors text-foreground hover:text-primary"
                                                        onClick={() => {
                                                            setModalAgent(agent.name);
                                                            setIsModalOpen(true);
                                                        }}
                                                    >
                                                        {isAssistant && '🎯 '}
                                                        {!isAssistant && isActive && '💬 '}
                                                        {agentInfo.displayName}
                                                    </span>
                                                </RunbookTooltip>
                                                <p className="text-xs text-muted-foreground leading-relaxed">
                                                    {agentInfo.description}
                                                </p>
                                                <p className="text-xs text-muted-foreground">
                                                    PID: {agent.pid || 'N/A'}
                                                </p>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-lg text-xs font-bold uppercase tracking-wide transition-all duration-200 ${
                                                agent.status === 'running'
                                                    ? 'bg-blue-600 text-white shadow-md shadow-blue-600/25 border border-blue-500'
                                                    : 'bg-slate-500 text-white shadow-md shadow-slate-500/25 border border-slate-400'
                                            }`}>
                                                <div className={`w-1.5 h-1.5 rounded-full ${
                                                    agent.status === 'running'
                                                        ? 'bg-blue-200 animate-pulse'
                                                        : 'bg-slate-300'
                                                }`} />
                                                <span>{agent.status}</span>
                                            </div>
                                            {agent.status === 'running' ? (
                                                <Button
                                                    variant="outline"
                                                    size="sm"
                                                    onClick={(e) => {
                                                        e.stopPropagation();  // Prevent card click
                                                        handleStop(agent.id);
                                                    }}
                                                    disabled={loading}
                                                    className="h-8 rounded-lg font-medium text-xs transition-all duration-200 bg-white hover:bg-gray-50 text-gray-700 hover:text-gray-800 border-2 border-gray-300 hover:border-gray-400 shadow-sm hover:shadow-md"
                                                >
                                                    ⏹️ Stop
                                                </Button>
                                            ) : (
                                                <Button
                                                    variant="default"
                                                    size="sm"
                                                    onClick={(e) => {
                                                        e.stopPropagation();  // Prevent card click
                                                        handleStart(agent.name, false);
                                                    }}
                                                    disabled={loading}
                                                    className="h-8 rounded-lg text-white shadow-lg hover:shadow-xl transition-all duration-200 font-medium text-xs bg-blue-600 hover:bg-blue-700"
                                                >
                                                    ▶️ Start
                                                </Button>
                                            )}
                                            {!isAssistant && (
                                                <Button
                                                    variant="outline"
                                                    size="sm"
                                                    onClick={(e) => {
                                                        e.stopPropagation();  // Prevent card click
                                                        if (window.confirm(`Delete ${agent.name} and its runbook?`)) {
                                                            deleteAgent(agent.name);
                                                        }
                                                    }}
                                                    disabled={loading}
                                                    className="h-8 rounded-lg font-medium text-xs transition-all duration-200 bg-red-50 hover:bg-red-100 text-red-700 hover:text-red-800 border-2 border-red-300 hover:border-red-400 shadow-sm hover:shadow-md"
                                                    title={`Delete ${agent.name}`}
                                                >
                                                    🗑️
                                                </Button>
                                            )}
                                        </div>
                                    </div>
                                </div>
                                );
                            })}
                        </div>
                    </div>
                </CardContent>
            </Card>
            
            {modalAgent && (
                <RunbookModal
                    agentName={modalAgent}
                    isOpen={isModalOpen}
                    onClose={() => {
                        setIsModalOpen(false);
                        setModalAgent(null);
                    }}
                />
            )}
        </>
    );
}
