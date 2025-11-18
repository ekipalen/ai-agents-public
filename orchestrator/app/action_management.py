"""Action server management and MCP integration."""
import os
import re
import json
from pathlib import Path
from typing import Dict, Any
from sqlalchemy.orm import Session
from . import models
from .action_client import ActionServerClient
from .database import SessionLocal


def substitute_env_vars(value: str) -> str:
    """Substitute environment variables in a string.

    Supports ${VAR_NAME} syntax.
    """
    if not isinstance(value, str):
        return value

    def replacer(match):
        var_name = match.group(1)
        env_value = os.getenv(var_name)
        if env_value:
            print(f"      🔑 Substituted ${{{var_name}}} -> {env_value[:30]}...")
            return env_value
        else:
            print(f"      ⚠️  Env var ${{{var_name}}} not found, keeping original")
            return match.group(0)

    return re.sub(r'\$\{([^}]+)\}', replacer, value)


def load_action_servers_config() -> Dict[str, Dict[str, Any]]:
    """Load action servers configuration from action_servers.json with env var substitution."""
    action_servers = {}
    config_file = Path("../action_servers.json")
    if not config_file.exists():
        print(f"⚠️  Action servers config not found at {config_file}")
        return action_servers

    try:
        with open(config_file, 'r') as f:
            config = json.load(f)

        servers = config.get("servers", {})
        for server_name, server_config in servers.items():
            # Substitute environment variables in url and token
            processed_config = {**server_config}
            processed_config["url"] = substitute_env_vars(server_config.get("url", ""))
            processed_config["token"] = substitute_env_vars(server_config.get("token", ""))

            action_servers[server_name] = processed_config
            print(f"🔌 Loaded action server: {server_name} ({processed_config.get('type', 'unknown')}) - {processed_config.get('url', 'no url')}")

        print(f"🔌 Loaded {len(action_servers)} action server(s)")

    except Exception as e:
        print(f"❌ Failed to load action servers config: {e}")

    return action_servers


def load_agent_action_configs(action_servers: Dict[str, Dict[str, Any]]):
    """Load agent action configurations from agent_configs directory with auto-discovery support."""
    configs_dir = Path("../agent_configs")
    if not configs_dir.exists():
        print(f"⚠️  Agent configs directory not found at {configs_dir}")
        return

    db = SessionLocal()
    loaded_count = 0

    try:
        config_files = list(configs_dir.glob("*.json"))
        print(f"📋 Found {len(config_files)} agent config file(s)")

        for config_file in config_files:
            agent_name = config_file.stem
            print(f"\n📝 Processing config for: {agent_name}")

            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)

                # Get or create agent in database
                agent = db.query(models.Agent).filter(models.Agent.name == agent_name).first()
                if not agent:
                    # Create agent stub entry for action configuration
                    print(f"   ⚠️  Agent not in database yet, creating entry...")
                    agent = models.Agent(
                        id=f"agent_{agent_name}",
                        name=agent_name,
                        role="Agent with actions",
                        inbox_topic=f"agent:{agent_name}:inbox",
                        status="stopped",
                        last_seen_at=0
                    )
                    db.add(agent)
                    db.commit()
                    db.refresh(agent)
                    print(f"   ✓ Created agent entry in database")
                else:
                    print(f"   ✓ Found agent in database")

                # Update agent with action server reference
                action_server_name = config.get("action_server")
                print(f"   ✓ Server reference: {action_server_name}")

                if action_server_name and action_server_name not in action_servers:
                    print(f"   ⚠️  Server not in loaded servers: {list(action_servers.keys())}")
                    continue

                agent.action_server_name = action_server_name

                # Check if server has auto_discover enabled
                server_config = action_servers.get(action_server_name, {})
                auto_discover = server_config.get("auto_discover", False)
                print(f"   ✓ Auto-discover: {auto_discover}")

                if auto_discover:
                    print(f"   🔍 Auto-discovering actions...")
                    print(f"      Server config: {server_config}")
                    print(f"      URL: {server_config.get('url')}")
                    print(f"      Token: {server_config.get('token')[:20] if server_config.get('token') else 'NONE'}...")

                    try:
                        print(f"      Creating ActionServerClient...")
                        # Create client and fetch actions from OpenAPI spec
                        client = ActionServerClient(
                            base_url=server_config["url"],
                            bearer_token=server_config.get("token")  # Optional for MCP servers
                        )
                        print(f"      ✓ Client created, calling list_actions()...")
                        discovered_actions = client.list_actions()
                        print(f"      ✓ list_actions() returned {len(discovered_actions)} actions")

                        # Convert to dict format
                        agent.actions = [action.to_dict() for action in discovered_actions]
                        print(f"   ✅ Auto-discovered {len(agent.actions)} actions!")

                    except Exception as e:
                        print(f"   ⚠️  Auto-discovery failed: {e}")
                        import traceback
                        traceback.print_exc()
                        # Fall back to manual config if available
                        agent.actions = config.get("actions", [])
                else:
                    # Use manual configuration from file
                    agent.actions = config.get("actions", [])

                db.commit()
                print(f"   🔧 Saved {len(agent.actions)} action(s)")
                loaded_count += 1

            except Exception as e:
                print(f"   ⚠️  Failed: {e}")
                import traceback
                traceback.print_exc()
                db.rollback()

        print(f"\n🔧 Loaded {loaded_count} agent action configurations")

    finally:
        db.close()
