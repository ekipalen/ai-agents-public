// Shared types for agent runbook data

export interface RunbookData {
  agent_name: string;
  role: string;
  capabilities: Array<{
    name: string;
    description: string;
    parameters?: Record<string, unknown>;
    example_usage?: string;
    tags?: string[];
  }>;
  collaboration_patterns?: string[];
  dependencies?: string[];
}
