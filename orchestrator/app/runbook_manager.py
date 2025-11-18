"""Runbook loading and management."""
import sys
from pathlib import Path
from typing import Dict, Any


def load_runbooks_from_filesystem() -> Dict[str, Dict[str, Any]]:
    """Load all agent runbooks from the runbooks directory."""
    agent_runbooks = {}
    runbooks_dir = Path("../runbooks")
    if not runbooks_dir.exists():
        print(f"⚠️  Runbooks directory not found at {runbooks_dir}")
        return agent_runbooks

    # Import RunbookLoader with proper path setup
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    sys.path.insert(0, str(project_root / "agentkit"))

    from agentkit.runbook_loader import RunbookLoader
    loader = RunbookLoader(str(runbooks_dir))

    loaded_count = 0
    for runbook_file in runbooks_dir.glob("*.md"):
        agent_name = runbook_file.stem
        try:
            runbook = loader.load_runbook(agent_name)
            # Convert to the format expected by the API
            agent_runbooks[agent_name] = {
                "agent_name": runbook.agent_name,
                "role": runbook.role,
                "capabilities": [
                    {
                        "name": cap.name,
                        "description": cap.description,
                        "parameters": cap.parameters,
                        "example_usage": cap.example_usage,
                        "tags": cap.tags
                    }
                    for cap in runbook.capabilities
                ],
                "collaboration_patterns": runbook.collaboration_patterns,
                "dependencies": runbook.dependencies
            }
            print(f"📚 Loaded runbook for agent: {agent_name}")
            loaded_count += 1
        except Exception as e:
            print(f"⚠️  Failed to load runbook for {agent_name}: {e}")

    print(f"📚 Loaded {loaded_count} agent runbooks from filesystem")
    return agent_runbooks
