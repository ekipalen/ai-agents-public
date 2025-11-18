"""OpenAI integration for agents."""
from typing import List, Dict, Optional, Iterator
from openai import OpenAI
from .constants import DEFAULT_MODEL


class AIClient:
    """Handles OpenAI API interactions for agents."""

    def __init__(self, api_key: str, agent_name: str, model: str = DEFAULT_MODEL):
        self.agent_name = agent_name
        self.model = model
        self.client = OpenAI(api_key=api_key) if api_key else None

        if not self.client:
            print(f"[{agent_name}] WARNING: OpenAI client not initialized (no API key)", flush=True)

    def get_completion(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> Optional[str]:
        """
        Get a completion from OpenAI.

        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt to prepend
            temperature: Sampling temperature (0-2)

        Returns:
            Response content or None on error
        """
        if not self.client:
            print(f"[{self.agent_name}] Cannot get completion, OpenAI client not initialized.", flush=True)
            return None

        # Prepend system prompt if provided
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages

        try:
            # Build API call parameters
            api_params = {
                "model": self.model,
                "messages": messages,
            }
            # Only add temperature if explicitly provided
            if temperature is not None:
                api_params["temperature"] = temperature

            response = self.client.chat.completions.create(**api_params)
            return response.choices[0].message.content
        except Exception as e:
            print(f"[{self.agent_name}] Error calling OpenAI: {e}", flush=True)
            return None

    def get_streaming_completion(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        functions: Optional[List[Dict]] = None,
        temperature: Optional[float] = None
    ) -> Iterator[str]:
        """
        Get a streaming completion from OpenAI.

        Args:
            messages: List of message dicts
            system_prompt: Optional system prompt
            functions: Optional function definitions for function calling
            temperature: Sampling temperature

        Yields:
            Content chunks or function call indicators (FUNC:name:args)
        """
        if not self.client:
            print(f"[{self.agent_name}] Cannot get streaming completion, OpenAI client not initialized.", flush=True)
            return

        # Prepend system prompt if provided
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages

        try:
            # Build API call parameters
            api_params = {
                "model": self.model,
                "messages": messages,
                "stream": True,
            }
            # Only add temperature if explicitly provided
            if temperature is not None:
                api_params["temperature"] = temperature

            # Create stream with optional function calling
            if functions:
                api_params["functions"] = functions
                api_params["function_call"] = "auto"
                stream = self.client.chat.completions.create(**api_params)
            else:
                stream = self.client.chat.completions.create(**api_params)

            current_function_call = None

            for chunk in stream:
                delta = chunk.choices[0].delta

                # Handle function calls
                if hasattr(delta, 'function_call') and delta.function_call:
                    function_call_delta = delta.function_call

                    # Start new function call
                    if function_call_delta.name:
                        if current_function_call:
                            # Finish previous function call
                            yield f"FUNC:{current_function_call['name']}:{current_function_call['arguments']}"
                        current_function_call = {
                            'name': function_call_delta.name,
                            'arguments': function_call_delta.arguments or ''
                        }
                    elif function_call_delta.arguments and current_function_call:
                        # Continue accumulating arguments
                        current_function_call['arguments'] += function_call_delta.arguments

                elif current_function_call:
                    # Finish current function call and reset
                    yield f"FUNC:{current_function_call['name']}:{current_function_call['arguments']}"
                    current_function_call = None

                    # Handle regular content if present
                    if delta.content:
                        yield delta.content
                else:
                    # Handle regular content
                    if delta.content:
                        yield delta.content

            # Finish any remaining function call
            if current_function_call:
                yield f"FUNC:{current_function_call['name']}:{current_function_call['arguments']}"

        except Exception as e:
            print(f"[{self.agent_name}] Error in OpenAI stream: {e}", flush=True)
