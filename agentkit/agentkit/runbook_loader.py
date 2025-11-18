"""
Runbook loader for parsing markdown runbook files into AgentRunbook objects.
"""

import re
from pathlib import Path
from typing import List, Dict, Any
from .base import AgentRunbook, AgentCapability


class RunbookLoader:
    """Loads and parses agent runbooks from markdown files."""

    def __init__(self, runbooks_dir: str = "runbooks"):
        """
        Initialize the runbook loader.

        Args:
            runbooks_dir: Directory containing runbook markdown files (relative to project root)
        """
        self.runbooks_dir = Path(runbooks_dir)
        self.runbooks_dir.mkdir(exist_ok=True)

    def load_runbook(self, agent_name: str) -> AgentRunbook:
        """
        Load a runbook for the specified agent.

        Args:
            agent_name: Name of the agent (e.g., 'assistant', 'researcher')

        Returns:
            AgentRunbook object with parsed capabilities and metadata
        """
        runbook_file = self.runbooks_dir / f"{agent_name}.md"

        if not runbook_file.exists():
            raise FileNotFoundError(f"Runbook file not found: {runbook_file}")

        content = runbook_file.read_text(encoding='utf-8')
        return self._parse_markdown_runbook(agent_name, content)

    def _parse_markdown_runbook(self, agent_name: str, content: str) -> AgentRunbook:
        """Parse markdown content into an AgentRunbook object."""
        # Extract sections
        job_title = self._extract_job_title(content)
        role = self._extract_role(content)
        capabilities = self._extract_capabilities(content)
        collaboration_patterns = self._extract_collaboration_patterns(content)
        dependencies = self._extract_dependencies(content)

        return AgentRunbook(
            agent_name=agent_name,
            role=role,
            job_title=job_title,  # Add job title to the runbook
            capabilities=capabilities,
            collaboration_patterns=collaboration_patterns,
            dependencies=dependencies
        )

    def _extract_job_title(self, content: str) -> str:
        """Extract the job title from the Job Title section."""
        job_title_match = re.search(r'## Job Title\s*\n(.*?)(?=\n## |\n##$|$)', content, re.DOTALL)
        if not job_title_match:
            return "AI Agent"  # Default fallback
        return job_title_match.group(1).strip()

    def _extract_role(self, content: str) -> str:
        """Extract the role description from the Role section."""
        role_match = re.search(r'## Role\s*\n(.*?)(?=\n## |\n##$|$)', content, re.DOTALL)
        if not role_match:
            return "No role description provided"
        return role_match.group(1).strip()

    def _extract_capabilities(self, content: str) -> List[AgentCapability]:
        """Extract capabilities from the Capabilities or Core Capabilities section."""
        capabilities = []

        # Find the Capabilities section (try both "Capabilities" and "Core Capabilities")
        cap_match = re.search(r'## (?:Core\s+)?Capabilities\s*\n(.*?)(?=\n## |\n##$|$)', content, re.DOTALL)
        if not cap_match:
            return capabilities

        cap_content = cap_match.group(1)

        # Try parsing as bullet point format first (like Lisa's runbook)
        bullet_capabilities = self._parse_bullet_capabilities(cap_content)
        if bullet_capabilities:
            return bullet_capabilities

        # Fallback to original format (### headers)
        capability_blocks = re.split(r'###\s+', cap_content)

        for block in capability_blocks:
            if not block.strip():
                continue

            capability = self._parse_capability_block(block.strip())
            if capability:
                capabilities.append(capability)

        return capabilities

    def _parse_bullet_capabilities(self, content: str) -> List[AgentCapability]:
        """Parse capabilities in bullet point format like Lisa's runbook."""
        capabilities = []
        lines = content.split('\n')
        
        current_capability = None
        current_description = ""
        
        for line in lines:
            original_line = line
            line = line.strip()
            if not line:
                continue
                
            # Main capability (starts with "- " at beginning of line, not indented)
            if original_line.startswith('- ') and not original_line.startswith('  '):
                # Save previous capability if exists
                if current_capability:
                    capabilities.append(AgentCapability(
                        name=current_capability,
                        description=current_description.strip(),
                        parameters={},
                        example_usage="",
                        tags=[current_capability.lower().replace(' ', '_')]
                    ))
                
                # Start new capability
                current_capability = line[2:].strip()
                current_description = ""
                
            # Sub-description (starts with "  - " - indented bullet point)
            elif original_line.startswith('  - ') and current_capability:
                desc = line[2:].strip()  # Remove "- " from stripped line
                if current_description:
                    current_description += " "
                current_description += desc
        
        # Don't forget the last capability
        if current_capability:
            capabilities.append(AgentCapability(
                name=current_capability,
                description=current_description.strip(),
                parameters={},
                example_usage="",
                tags=[current_capability.lower().replace(' ', '_')]
            ))
        
        return capabilities

    def _parse_capability_block(self, block: str) -> AgentCapability:
        """Parse a single capability block."""
        lines = block.split('\n')
        if not lines:
            return None

        # First line is the capability name
        name = lines[0].strip()

        description = ""
        parameters = {}
        example_usage = ""
        tags = []

        i = 1
        while i < len(lines):
            line = lines[i].strip()

            if line.startswith('- **Description**:'):
                description = line.replace('- **Description**:', '').strip()
            elif line.startswith('- **Parameters**:'):
                # Parameters might span multiple lines
                params_text = ""
                i += 1
                while i < len(lines) and not lines[i].strip().startswith('- **'):
                    if lines[i].strip():
                        params_text += lines[i].strip() + " "
                    i += 1
                # Parse parameters (simple key: value format)
                if params_text.strip():
                    for param_line in params_text.split('\n'):
                        param_line = param_line.strip()
                        if ':' in param_line:
                            key, value = param_line.split(':', 1)
                            parameters[key.strip()] = value.strip()
                i -= 1  # Adjust back since we consumed the next line
            elif line.startswith('- **Example Usage**:'):
                example_usage = line.replace('- **Example Usage**:', '').strip()
            elif line.startswith('- **Tags**:'):
                tags_text = line.replace('- **Tags**:', '').strip()
                if tags_text:
                    tags = [tag.strip() for tag in tags_text.split(',')]

            i += 1

        return AgentCapability(
            name=name,
            description=description,
            parameters=parameters,
            example_usage=example_usage,
            tags=tags
        )

    def _extract_collaboration_patterns(self, content: str) -> List[str]:
        """Extract collaboration patterns from the Collaboration Patterns section."""
        patterns = []

        pattern_match = re.search(r'## Collaboration Patterns\s*\n(.*?)(?=\n## |\n##$|$)', content, re.DOTALL)
        if not pattern_match:
            return patterns

        pattern_content = pattern_match.group(1)

        # Split by bullet points
        for line in pattern_content.split('\n'):
            line = line.strip()
            if line.startswith('- '):
                patterns.append(line[2:].strip())

        return patterns

    def _extract_dependencies(self, content: str) -> List[str]:
        """Extract dependencies from the Dependencies section."""
        dependencies = []

        dep_match = re.search(r'## Dependencies\s*\n(.*?)(?=\n## |\n##$|$)', content, re.DOTALL)
        if not dep_match:
            return dependencies

        dep_content = dep_match.group(1)

        # Split by lines
        for line in dep_content.split('\n'):
            line = line.strip()
            if line.startswith('- '):
                dependencies.append(line[2:].strip())
            elif line and not line.startswith('#'):
                dependencies.append(line)

        return dependencies

    def list_available_runbooks(self) -> List[str]:
        """List all available runbook files."""
        if not self.runbooks_dir.exists():
            return []

        return [f.stem for f in self.runbooks_dir.glob('*.md')]

    def validate_runbook(self, agent_name: str) -> Dict[str, Any]:
        """
        Validate a runbook file and return validation results.

        Returns:
            Dict with 'valid': bool and 'errors': List[str]
        """
        try:
            runbook = self.load_runbook(agent_name)

            errors = []

            if not runbook.role or runbook.role == "No role description provided":
                errors.append("Missing or empty role description")

            if not runbook.capabilities:
                errors.append("No capabilities defined")

            # Check each capability has required fields
            for cap in runbook.capabilities:
                if not cap.name:
                    errors.append(f"Capability missing name")
                if not cap.description:
                    errors.append(f"Capability '{cap.name}' missing description")

            return {
                'valid': len(errors) == 0,
                'errors': errors,
                'runbook': runbook
            }

        except Exception as e:
            return {
                'valid': False,
                'errors': [f"Failed to load runbook: {str(e)}"],
                'runbook': None
            }
