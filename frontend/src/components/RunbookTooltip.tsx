import { useState, useEffect } from 'react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { RunbookData } from '@/types/runbook';
import { getApiUrl } from '@/config/api';

interface RunbookTooltipProps {
    agentName: string;
    children: React.ReactNode;
}

export function RunbookTooltip({ agentName, children }: RunbookTooltipProps) {
    const [runbook, setRunbook] = useState<RunbookData | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchRunbook = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await fetch(getApiUrl(`/agents/runbooks/${agentName}`));
            if (!response.ok) {
                throw new Error('Runbook not found');
            }
            const data = await response.json();
            setRunbook(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to fetch runbook');
        } finally {
            setLoading(false);
        }
    };

    const formatRunbookContent = (runbook: RunbookData) => {
        return (
            <div className="space-y-3 text-gray-900 dark:text-gray-100">
                <div className="border-b border-gray-200 dark:border-gray-600 pb-2">
                    <h4 className="font-bold text-blue-600 dark:text-blue-400 text-sm mb-1 break-words">
                        {runbook.agent_name}
                    </h4>
                    <p className="text-xs text-gray-600 dark:text-gray-400 italic">{runbook.role}</p>
                </div>
                
                {runbook.capabilities && runbook.capabilities.length > 0 && (
                    <div>
                        <h5 className="font-semibold text-xs mb-2 text-gray-700 dark:text-gray-300 uppercase tracking-wide">
                            Capabilities:
                        </h5>
                        <ul className="text-xs space-y-1">
                            {runbook.capabilities.slice(0, 3).map((cap, index) => (
                                <li key={index} className="text-gray-600 dark:text-gray-400 flex items-start">
                                    <span className="text-blue-500 mr-2">•</span>
                                    <span className="break-words">{cap.name}</span>
                                </li>
                            ))}
                            {runbook.capabilities.length > 3 && (
                                <li className="text-gray-500 dark:text-gray-500 text-xs italic">
                                    +{runbook.capabilities.length - 3} more capabilities...
                                </li>
                            )}
                        </ul>
                    </div>
                )}
                
                {runbook.collaboration_patterns && runbook.collaboration_patterns.length > 0 && (
                    <div>
                        <h5 className="font-semibold text-xs mb-2 text-gray-700 dark:text-gray-300 uppercase tracking-wide">
                            Collaboration:
                        </h5>
                        <p className="text-xs text-gray-600 dark:text-gray-400 break-words">
                            {runbook.collaboration_patterns.slice(0, 2).join(', ')}
                            {runbook.collaboration_patterns.length > 2 && '...'}
                        </p>
                    </div>
                )}
            </div>
        );
    };

    return (
        <TooltipProvider>
            <Tooltip>
                <TooltipTrigger 
                    asChild 
                    onMouseEnter={fetchRunbook}
                >
                    {children}
                </TooltipTrigger>
                <TooltipContent 
                    side="top" 
                    className="max-w-md p-4 bg-white dark:bg-slate-800 border-2 border-blue-200 dark:border-blue-600 shadow-xl rounded-lg z-50"
                    sideOffset={10}
                    avoidCollisions={true}
                    collisionPadding={20}
                >
                    {loading && (
                        <div className="text-sm text-blue-600 dark:text-blue-400 flex items-center gap-2">
                            <div className="w-3 h-3 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                            Loading runbook...
                        </div>
                    )}
                    {error && (
                        <div className="text-sm text-red-600 dark:text-red-400 p-2 bg-red-50 dark:bg-red-900/20 rounded border border-red-200 dark:border-red-700">
                            <span className="font-medium">⚠️ {error}</span>
                        </div>
                    )}
                    {runbook && formatRunbookContent(runbook)}
                </TooltipContent>
            </Tooltip>
        </TooltipProvider>
    );
}
