import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RunbookData } from '@/types/runbook';
import { getApiUrl } from '@/config/api';

interface RunbookModalProps {
    agentName: string;
    isOpen: boolean;
    onClose: () => void;
}

export function RunbookModal({ agentName, isOpen, onClose }: RunbookModalProps) {
    const [runbook, setRunbook] = useState<RunbookData | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (isOpen && agentName) {
            fetchRunbook();
        }
    }, [isOpen, agentName]);

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

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-background rounded-lg shadow-lg max-w-2xl w-full max-h-[80vh] overflow-y-auto">
                <Card>
                    <CardHeader>
                        <div className="flex items-center justify-between">
                            <CardTitle className="text-xl">
                                {runbook?.agent_name || agentName} Runbook
                            </CardTitle>
                            <button
                                onClick={onClose}
                                className="text-muted-foreground hover:text-foreground transition-colors"
                            >
                                ✕
                            </button>
                        </div>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        {loading && (
                            <div className="text-center py-8">
                                <div className="text-muted-foreground">Loading runbook...</div>
                            </div>
                        )}
                        
                        {error && (
                            <div className="text-center py-8">
                                <div className="text-destructive">{error}</div>
                            </div>
                        )}
                        
                        {runbook && (
                            <>
                                <div>
                                    <h3 className="font-semibold text-lg mb-2">Role</h3>
                                    <p className="text-muted-foreground">{runbook.role}</p>
                                </div>
                                
                                {runbook.capabilities && runbook.capabilities.length > 0 && (
                                    <div>
                                        <h3 className="font-semibold text-lg mb-3">Capabilities</h3>
                                        <div className="space-y-4">
                                            {runbook.capabilities.map((cap, index) => (
                                                <div key={index} className="border rounded-lg p-4">
                                                    <h4 className="font-medium mb-2">{cap.name}</h4>
                                                    <p className="text-sm text-muted-foreground mb-2">
                                                        {cap.description}
                                                    </p>
                                                    {cap.example_usage && (
                                                        <div className="mt-2">
                                                            <h5 className="text-xs font-medium text-muted-foreground mb-1">
                                                                Example Usage:
                                                            </h5>
                                                            <pre className="text-xs bg-muted p-2 rounded overflow-x-auto">
                                                                {cap.example_usage}
                                                            </pre>
                                                        </div>
                                                    )}
                                                    {cap.tags && cap.tags.length > 0 && (
                                                        <div className="mt-2 flex flex-wrap gap-1">
                                                            {cap.tags.map((tag, tagIndex) => (
                                                                <span
                                                                    key={tagIndex}
                                                                    className="text-xs bg-primary/10 text-primary px-2 py-1 rounded"
                                                                >
                                                                    {tag}
                                                                </span>
                                                            ))}
                                                        </div>
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                                
                                {runbook.collaboration_patterns && runbook.collaboration_patterns.length > 0 && (
                                    <div>
                                        <h3 className="font-semibold text-lg mb-2">Collaboration Patterns</h3>
                                        <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                                            {runbook.collaboration_patterns.map((pattern, index) => (
                                                <li key={index}>{pattern}</li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                                
                                {runbook.dependencies && runbook.dependencies.length > 0 && (
                                    <div>
                                        <h3 className="font-semibold text-lg mb-2">Dependencies</h3>
                                        <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                                            {runbook.dependencies.map((dep, index) => (
                                                <li key={index}>{dep}</li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
