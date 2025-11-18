# orchestrator/app/action_client.py
"""
Client for interacting with Action Servers (MCP, OpenAPI-based servers).
Supports fetching OpenAPI specs and executing actions.
"""
import requests
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json


@dataclass
class ActionParameter:
    """Represents a parameter for an action."""
    name: str
    type: str
    description: str
    required: bool


@dataclass
class Action:
    """Represents an action from an action server."""
    id: str  # operation_id from OpenAPI
    name: str  # summary from OpenAPI
    description: str  # description from OpenAPI
    endpoint: str  # path like /send-email
    method: str  # HTTP method (usually POST)
    parameters: List[ActionParameter]
    response_schema: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "endpoint": self.endpoint,
            "method": self.method,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type,
                    "description": p.description,
                    "required": p.required
                }
                for p in self.parameters
            ],
            "response_schema": self.response_schema,
            "enabled": True
        }


class ActionServerClient:
    """Client for interacting with Action Servers (MCP, OpenAPI-based servers)."""

    def __init__(self, base_url: str, bearer_token: Optional[str] = None):
        """
        Initialize Action Server Client.

        Args:
            base_url: Base URL of the action server (e.g., http://localhost:8000)
            bearer_token: Optional bearer token for authentication (None for no auth)
        """
        print(f"\n🔧 Initializing ActionServerClient")
        print(f"   Base URL: {base_url}")
        print(f"   Auth: {'Yes' if bearer_token else 'No authentication'}")

        self.base_url = base_url.rstrip('/')
        self.bearer_token = bearer_token

        # Build headers
        self.headers = {"Content-Type": "application/json"}
        if bearer_token:
            self.headers["Authorization"] = f"Bearer {bearer_token}"

        print(f"   ✓ Client initialized")

    def fetch_openapi_spec(self) -> Optional[Dict[str, Any]]:
        """
        Fetch the OpenAPI specification from the action server.
        Tries multiple common endpoints.

        Returns:
            OpenAPI spec as dictionary, or None if failed
        """
        # Try common OpenAPI spec endpoints
        endpoints = ["/openapi.json", "", "/api/openapi.json", "/docs/openapi.json"]

        print(f"\n🔗 Fetching OpenAPI spec from: {self.base_url}")

        for endpoint in endpoints:
            try:
                url = f"{self.base_url}{endpoint}"
                print(f"   → Trying: {url}")

                response = requests.get(url, headers=self.headers, timeout=10)

                if response.status_code == 200:
                    try:
                        data = response.json()
                        # Verify it's an OpenAPI spec
                        if "openapi" in data or "swagger" in data:
                            print(f"      ✅ Found valid OpenAPI spec at {endpoint or '/'}")
                            return data
                        else:
                            print(f"      ⚠️  JSON but not OpenAPI format")
                    except ValueError:
                        print(f"      ⚠️  Not valid JSON")
                else:
                    print(f"      Status: {response.status_code}")

            except requests.RequestException as e:
                print(f"      ❌ Error: {type(e).__name__}: {str(e)[:50]}")

        print(f"\n❌ Failed to fetch OpenAPI spec after trying all endpoints")
        return None

    def parse_actions(self, openapi_spec: Dict[str, Any]) -> List[Action]:
        """
        Parse OpenAPI spec to extract available actions.

        Args:
            openapi_spec: OpenAPI specification dictionary

        Returns:
            List of Action objects
        """
        actions = []
        paths = openapi_spec.get("paths", {})

        for path, methods in paths.items():
            # Skip health check and meta endpoints
            if path in ["/", "/health", "/tools"]:
                continue

            for method, details in methods.items():
                method_upper = method.upper()

                # Extract action metadata
                operation_id = details.get("operationId", "")
                summary = details.get("summary", "")
                description = details.get("description", "")

                # Parse request body schema to get parameters
                parameters = []
                request_body = details.get("requestBody", {})
                content = request_body.get("content", {})
                json_schema = content.get("application/json", {}).get("schema", {})

                # Handle $ref in schema
                if "$ref" in json_schema:
                    ref_path = json_schema["$ref"]
                    # Extract referenced schema (e.g., #/components/schemas/SendEmailRequest)
                    ref_parts = ref_path.split("/")
                    if len(ref_parts) >= 4 and ref_parts[0] == "#":
                        components = openapi_spec.get("components", {})
                        schemas = components.get("schemas", {})
                        schema_name = ref_parts[-1]
                        json_schema = schemas.get(schema_name, {})

                properties = json_schema.get("properties", {})
                required_fields = json_schema.get("required", [])

                for param_name, param_schema in properties.items():
                    # Handle anyOf type (optional fields in MCP)
                    param_type = "string"  # default
                    if "anyOf" in param_schema:
                        # Take first non-null type
                        for type_option in param_schema["anyOf"]:
                            if type_option.get("type") != "null":
                                param_type = type_option.get("type", "string")
                                break
                    else:
                        param_type = param_schema.get("type", "string")

                    param_desc = param_schema.get("description", "")
                    param_required = param_name in required_fields

                    parameters.append(ActionParameter(
                        name=param_name,
                        type=param_type,
                        description=param_desc,
                        required=param_required
                    ))

                # Parse response schema
                responses = details.get("responses", {})
                success_response = responses.get("200", {})
                response_content = success_response.get("content", {})
                response_schema = response_content.get("application/json", {}).get("schema", {})

                # Create Action object
                action = Action(
                    id=operation_id,
                    name=summary or path.replace("/", "").replace("-", " ").title(),
                    description=description,
                    endpoint=path,
                    method=method_upper,
                    parameters=parameters,
                    response_schema=response_schema
                )
                actions.append(action)

        return actions

    def list_actions(self) -> List[Action]:
        """
        List all available actions from the action server.

        Returns:
            List of Action objects
        """
        print(f"\n🔍 Discovering actions from action server...")
        openapi_spec = self.fetch_openapi_spec()

        if not openapi_spec:
            print(f"   ❌ No OpenAPI spec returned")
            return []

        print(f"   ✓ Got OpenAPI spec, parsing actions...")
        actions = self.parse_actions(openapi_spec)
        print(f"   ✅ Found {len(actions)} action(s)")
        return actions

    def execute_action(self, endpoint: str, parameters: Dict[str, Any], method: str = "POST") -> Dict[str, Any]:
        """
        Execute an action on the action server.

        Args:
            endpoint: Action endpoint path (e.g., /send-email)
            parameters: Dictionary of parameters for the action
            method: HTTP method (default: POST)

        Returns:
            Response dictionary
        """
        try:
            url = f"{self.base_url}{endpoint}"

            print(f"   🔧 Executing action: {method} {url}")
            print(f"   📤 Parameters being sent: {parameters}")

            if method.upper() == "POST":
                response = requests.post(
                    url,
                    headers=self.headers,
                    json=parameters,
                    timeout=30
                )
            elif method.upper() == "GET":
                response = requests.get(
                    url,
                    headers=self.headers,
                    params=parameters,
                    timeout=30
                )
            else:
                return {"error": f"Unsupported HTTP method: {method}"}

            print(f"   ✅ Response status: {response.status_code}")
            response.raise_for_status()
            result = response.json()
            print(f"   📥 Response preview: {str(result)[:200]}...")
            return result
        except requests.RequestException as e:
            print(f"   ❌ Request failed: {str(e)}")
            return {
                "error": f"Failed to execute action: {str(e)}"
            }

    def test_connection(self) -> bool:
        """
        Test if the action server is reachable.

        Returns:
            True if connection successful, False otherwise
        """
        openapi_spec = self.fetch_openapi_spec()
        return openapi_spec is not None
