"""Agent lifecycle management - start, stop, create, delete operations."""
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, Any
from sqlalchemy.orm import Session
from . import models


# In-memory storage for running agent processes
running_processes: Dict[str, Dict[str, Any]] = {}

LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)


def stop_agent_process(agent_name: str, db: Session) -> dict:
    """
    Stop an agent process cleanly. Handles both tracked processes and stale PIDs.

    Returns:
        dict with 'ok' (bool), 'message' (str), and optional 'error' (str)
    """
    db_agent = db.query(models.Agent).filter(models.Agent.name == agent_name).first()

    # Try to stop from tracked processes first
    proc_info = running_processes.get(agent_name)
    if proc_info:
        process = proc_info["process"]
        try:
            # Check if already dead
            if process.poll() is not None:
                print(f"Agent {agent_name} already stopped")
            else:
                # Graceful shutdown (SIGTERM)
                process.terminate()
                try:
                    process.wait(timeout=3)
                    print(f"Agent {agent_name} stopped gracefully")
                except subprocess.TimeoutExpired:
                    # Force kill (SIGKILL)
                    print(f"Agent {agent_name} didn't respond, force killing...")
                    process.kill()
                    process.wait(timeout=2)

            # Clean up log file
            try:
                if "log_file" in proc_info and proc_info["log_file"]:
                    proc_info["log_file"].close()
            except Exception:
                pass

            # Remove from tracking
            running_processes.pop(agent_name, None)

        except Exception as e:
            return {"ok": False, "error": f"Error stopping process: {e}"}

    # Handle stale PID in database
    elif db_agent and db_agent.pid and db_agent.status == "running":
        try:
            os.kill(db_agent.pid, subprocess.signal.SIGTERM)
            print(f"Killed stale process {db_agent.pid} for agent {agent_name}")
        except ProcessLookupError:
            print(f"Stale PID {db_agent.pid} for agent {agent_name} was already dead")
        except Exception as e:
            return {"ok": False, "error": f"Error killing stale PID: {e}"}

    # Update database
    if db_agent:
        db_agent.status = "stopped"
        db_agent.pid = None
        db.commit()
        return {"ok": True, "message": f"Agent '{agent_name}' stopped"}
    else:
        return {"ok": False, "error": f"Agent '{agent_name}' not found in database"}


def cleanup_stale_agents(db: Session):
    """
    Clean up stale agent records on startup.
    Checks if agents marked as 'running' in the database actually have running processes.
    Marks dead agents as 'stopped'.
    """
    print("🧹 Cleaning up stale agent records...")
    try:
        # Get all agents marked as running
        running_agents = db.query(models.Agent).filter(models.Agent.status == "running").all()

        cleaned_count = 0
        for agent in running_agents:
            # Check if PID exists and process is actually running
            if agent.pid:
                try:
                    # Check if process exists by sending signal 0 (doesn't kill, just checks)
                    os.kill(agent.pid, 0)
                    print(f"  ✓ Agent '{agent.name}' (PID {agent.pid}) is actually running")
                except (OSError, ProcessLookupError):
                    # Process doesn't exist
                    print(f"  ✗ Agent '{agent.name}' (PID {agent.pid}) is dead - marking as stopped")
                    agent.status = "stopped"
                    agent.pid = None
                    cleaned_count += 1
            else:
                # No PID recorded but marked as running - definitely stale
                print(f"  ✗ Agent '{agent.name}' has no PID but marked as running - marking as stopped")
                agent.status = "stopped"
                cleaned_count += 1

        db.commit()
        print(f"✅ Cleaned up {cleaned_count} stale agent record(s)")
    except Exception as e:
        print(f"❌ Error during stale agent cleanup: {e}")
        db.rollback()


def ensure_virtual_environment(agents_dir: Path) -> bool:
    """Ensure virtual environment is properly set up for agents."""
    try:
        print("🔧 Checking virtual environment setup...")

        # Check if uv is available
        uv_check = subprocess.run(['uv', '--version'],
                                capture_output=True, text=True, timeout=10)
        if uv_check.returncode != 0:
            print("❌ uv is not available. Please install uv first.")
            return False

        print("✅ uv is available")

        # Check if pyproject.toml exists (for uv dependency management)
        pyproject_path = agents_dir / "pyproject.toml"
        if not pyproject_path.exists():
            print("⚠️  No pyproject.toml found, using basic uv run")
            # uv run should handle venv creation automatically
            return True

        # Check if virtual environment exists
        venv_path = agents_dir / ".venv"
        if not venv_path.exists():
            print("📦 Creating virtual environment...")
            venv_result = subprocess.run(['uv', 'venv'],
                                       cwd=str(agents_dir),
                                       capture_output=True, text=True, timeout=30)

            if venv_result.returncode != 0:
                print(f"❌ Failed to create virtual environment: {venv_result.stderr}")
                return False

            print("✅ Virtual environment created")

        # Install/sync dependencies
        print("📦 Installing/syncing dependencies...")
        sync_result = subprocess.run(['uv', 'sync'],
                                   cwd=str(agents_dir),
                                   capture_output=True, text=True, timeout=60)

        if sync_result.returncode != 0:
            print(f"❌ Failed to sync dependencies: {sync_result.stderr}")
            return False

        print("✅ Dependencies installed/synced")
        return True

    except subprocess.TimeoutExpired:
        print("❌ Virtual environment setup timed out")
        return False
    except Exception as e:
        print(f"❌ Error setting up virtual environment: {e}")
        return False


def start_agent_by_name(agent_name: str) -> dict:
    """Internal function to start an agent by name. Returns dict with ok/error/message."""
    if agent_name in running_processes:
        return {"ok": False, "error": f"Agent '{agent_name}' is already running."}

    # Special case: Assistant should use its dedicated main.py, not worker agent
    if agent_name == "assistant":
        agent_dir = Path(f"../agents/{agent_name}")
        if not agent_dir.exists():
            return {"ok": False, "error": f"Assistant directory '{agent_dir}' not found."}

        main_py = agent_dir / "main.py"
        if not main_py.exists():
            return {"ok": False, "error": f"Assistant main.py not found."}

        # Traditional startup for assistant (it has specialized logic)
        try:
            log_file_path = LOGS_DIR / f"{agent_name}.log"
            log_file = open(log_file_path, "w")

            process = subprocess.Popen(
                ['uv', 'run', 'python', 'main.py'],
                cwd=str(agent_dir),
                stdout=log_file,
                stderr=log_file
            )

            running_processes[agent_name] = {"process": process, "log_file": log_file}

            return {"ok": True, "message": f"Assistant started with PID {process.pid}. Check logs/{agent_name}.log for details."}

        except Exception as e:
            return {"ok": False, "error": f"Failed to start assistant: {str(e)}"}

    # Check if this is a worker agent (has runbook but no dedicated folder)
    runbooks_dir = Path("../runbooks")
    runbook_file = runbooks_dir / f"{agent_name}.md"

    if runbook_file.exists():
        # This is a worker agent - use unified worker_agent.py
        try:
            log_file_path = LOGS_DIR / f"{agent_name}.log"
            log_file = open(log_file_path, "w")

            # Ensure virtual environment is set up before starting agent
            agents_dir = Path("../agents")
            venv_setup_success = ensure_virtual_environment(agents_dir)
            if not venv_setup_success:
                return {"ok": False, "error": f"Failed to set up virtual environment for agent '{agent_name}'"}

            # Use worker_agent.py with agent_type parameter
            # Force uv to skip cache and prevent Python bytecode caching
            process = subprocess.Popen(
                ['uv', 'run', '--no-cache', 'python', 'worker_agent.py', agent_name],
                cwd=str(agents_dir),
                stdout=log_file,
                stderr=subprocess.STDOUT,  # Combine stderr with stdout
                env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}  # Prevent .pyc files
            )

            running_processes[agent_name] = {"process": process, "log_file": log_file}

            print(f"✅ Worker agent '{agent_name}' started with PID {process.pid}")
            print(f"📝 Logs: {log_file_path}")

            return {"ok": True, "message": f"Worker agent '{agent_name}' is starting with PID {process.pid}. Check logs/{agent_name}.log for details."}

        except Exception as e:
            return {"ok": False, "error": f"Failed to start worker agent '{agent_name}': {str(e)}"}

    # Check for traditional agent with dedicated folder
    agent_dir = Path(f"../agents/{agent_name}")
    if not agent_dir.exists():
        return {"ok": False, "error": f"Agent directory '{agent_dir}' not found and no runbook found for '{agent_name}'."}

    main_py = agent_dir / "main.py"
    if not main_py.exists():
        return {"ok": False, "error": f"Agent is not properly configured (missing main.py)."}

    # Traditional agent startup
    try:
        log_file_path = LOGS_DIR / f"{agent_name}.log"
        log_file = open(log_file_path, "w")

        process = subprocess.Popen(
            ['uv', 'run', 'main.py'],
            cwd=str(agent_dir),
            stdout=log_file,
            stderr=log_file
        )

        running_processes[agent_name] = {"process": process, "log_file": log_file}

        return {"ok": True, "message": f"Agent '{agent_name}' is starting with PID {process.pid}. Check logs/{agent_name}.log for details."}
    except Exception as e:
        return {"ok": False, "error": f"Failed to start agent: {str(e)}"}


def generate_agent_runbook(agent_name: str, role: str, capabilities: list) -> str:
    """Generate a runbook markdown content for a new agent."""
    # Create capabilities section
    capabilities_md = ""
    for cap in capabilities:
        capabilities_md += f"- {cap.get('name', 'Task execution')}\n"
        if 'description' in cap:
            capabilities_md += f"  - {cap['description']}\n"

    # Extract job title from role (first few words) or use role as fallback
    job_title = role.split('.')[0].strip()  # Take first sentence as job title
    if len(job_title) > 50:  # If too long, use role description
        job_title = role

    # Generate the runbook content
    runbook = f"""# {agent_name.title()} Agent Runbook

## Job Title
{job_title}

## Role
{role}

## Core Capabilities
{capabilities_md}

## Key Principles
- Execute tasks based on your defined capabilities
- Provide helpful and accurate responses
- Work collaboratively with other agents when needed
- Maintain focus on your specialized role

## Task Assessment
Handle requests that align with your capabilities:
- Accept tasks within your defined role
- Decline tasks outside your scope
- Seek clarification when needed
- Provide clear, actionable results

## Available Tools
Use your capabilities to complete assigned tasks effectively.
"""

    return runbook


def parse_runbook_content(content: str) -> Dict[str, Any]:
    """Parse runbook markdown into structured data."""
    import re

    # Extract role
    role_match = re.search(r'## Role\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
    role = role_match.group(1).strip() if role_match else "AI Agent"

    # Extract capabilities
    cap_match = re.search(r'## Core Capabilities\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
    capabilities = []
    if cap_match:
        cap_lines = cap_match.group(1).strip().split('\n')
        for line in cap_lines:
            line = line.strip()
            if line.startswith('- ') and not line.startswith('  - '):
                capabilities.append({
                    "name": line[2:].strip(),
                    "description": "",
                    "parameters": [],
                    "example_usage": "",
                    "tags": []
                })

    return {
        "agent_name": content.split('\n')[0].replace('# ', '').lower(),
        "role": role,
        "capabilities": capabilities,
        "collaboration_patterns": [],
        "dependencies": []
    }
