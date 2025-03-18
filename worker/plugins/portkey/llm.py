# Copyright 2023 LiveKit, Inc.
#

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import os
import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Literal, Optional, Union

from livekit.agents import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    llm,
)
from livekit.agents.llm import (
    LLMCapabilities,
    ToolChoice,
    _create_ai_function_info,
)
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS, APIConnectOptions

from .models import PortkeyChatModels, ProviderOptions

from portkey_ai import Portkey
from portkey_ai.api_resources.exceptions import APITimeoutError as PortkeyAPITimeoutError
from portkey_ai.api_resources.exceptions import APIStatusError as PortkeyAPIStatusError


@dataclass
class LLMOptions:
    model: str | PortkeyChatModels
    temperature: Optional[float]
    parallel_tool_calls: Optional[bool]
    tool_choice: Union[ToolChoice, Literal["auto", "required", "none"]] = "auto"
    max_tokens: Optional[int] = None
    metadata: Optional[Dict[str, str]] = None
    config: Optional[Union[str, Dict[str, Any]]] = None
    virtual_key: Optional[str] = None


# Default settings for the Portkey client


def _get_api_key(env_var: str, key: str | None) -> str:
    """Helper function to get API key from environment or argument."""
    key = key or os.environ.get(env_var)
    if not key:
        raise ValueError(
            f"{env_var} is required, either as argument or set {env_var} environmental variable"
        )
    return key


def _strip_nones(data: dict[str, Any]) -> dict[str, Any]:
    """Remove None values from a dictionary."""
    return {k: v for k, v in data.items() if v is not None}


def _build_message(msg: llm.ChatMessage) -> Dict[str, Any]:
    """Convert a LiveKit ChatMessage to a Portkey message format."""
    message = {
        "role": msg.role,
        "content": msg.content,
    }
    
    # Add name if present
    if msg.name:
        message["name"] = msg.name
        
    return message


def _build_chat_context(chat_ctx: llm.ChatContext) -> List[Dict[str, Any]]:
    """Convert LiveKit ChatContext to Portkey messages format."""
    return [_build_message(msg) for msg in chat_ctx.messages]


class LLM(llm.LLM):
    def __init__(
        self,
        *,
        model: str | PortkeyChatModels = None,
        api_key: Optional[str] = None,
        temperature: Optional[float] = None,
        parallel_tool_calls: Optional[bool] = None,
        tool_choice: Union[ToolChoice, Literal["auto", "required", "none"]] = "auto",
        max_tokens: Optional[int] = 1024,
        metadata: Optional[Dict[str, str]] = None,
        config: Optional[Union[str, Dict[str, Any]]] = None,
        virtual_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ) -> None:
        """
        Create a new instance of Portkey LLM.

        ``api_key`` must be set to your Portkey API key, either using the argument or by setting the
        ``PORTKEY_API_KEY`` environmental variable.
        
        Parameters:
            model: The model to use for generating completions. Default is "gpt-4o".
            api_key: Your Portkey API key.
            temperature: Controls randomness. Higher values mean more random completions. Default is 0.7.
            parallel_tool_calls: Whether to allow parallel function calls.
            tool_choice: Controls which function is called by the model. Default is "auto".
            max_tokens: The maximum number of tokens to generate. Default is 1024.
            metadata: Additional metadata to include with the request (will be converted to JSON).
            config: A Portkey config string ID (e.g., "pc-xxxx") or a config dictionary with
                   settings to control routing, caching, and other Portkey features.
            virtual_key: A virtual key to use for the request.
            provider: The provider to use (e.g., "openai", "anthropic", etc.). Default is "openai".
            user: A unique identifier representing your end-user.
            api_base: The base URL for the Portkey API.
        
        Example:
            ```python
            # Create a Portkey LLM with OpenAI provider
            llm = LLM(
                model="gpt-4o",
                api_key="pk-...",
                provider="openai",
                config="pc-your-config-id",  # Your Portkey config ID
                metadata={"session_id": "user-123"},
            )
            
            # Create a Portkey LLM with Anthropic provider
            anthropic_llm = LLM(
                model="claude-3-opus-20240229",
                api_key="pk-...",
                provider="anthropic",
                temperature=0.5,
            )
            ```
        """
        super().__init__(
            capabilities=LLMCapabilities(
                supports_choices_on_int=True,
                requires_persistent_functions=False,
            )
        )

        self._opts = LLMOptions(
            model=model,
            temperature=temperature,
            parallel_tool_calls=parallel_tool_calls,
            tool_choice=tool_choice,
            max_tokens=max_tokens,
            metadata=metadata,
            config=config,
            virtual_key=virtual_key,
        )
        
        api_key = _get_api_key("PORTKEY_API_KEY", api_key)
        
        # Initialize Portkey client with proper defaults
        client_params = {}
        if api_base:
            client_params["base_url"] = api_base
        
        self._client = Portkey(
            api_key=api_key,
            **client_params
        )

    def chat(
        self,
        *,
        chat_ctx: llm.ChatContext,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
        fnc_ctx: Optional[llm.FunctionContext] = None,
        temperature: Optional[float] = None,
        n: Optional[int] = 1,
        parallel_tool_calls: Optional[bool] = None,
        tool_choice: Optional[Union[ToolChoice, Literal["auto", "required", "none"]]] = None,
    ) -> "LLMStream":
        if parallel_tool_calls is None:
            parallel_tool_calls = self._opts.parallel_tool_calls

        if tool_choice is None:
            tool_choice = self._opts.tool_choice

        if temperature is None:
            temperature = self._opts.temperature

        return LLMStream(
            self,
            client=self._client,
            model=self._opts.model,
            chat_ctx=chat_ctx,
            fnc_ctx=fnc_ctx,
            conn_options=conn_options,
            n=n,
            temperature=temperature,
            parallel_tool_calls=parallel_tool_calls,
            tool_choice=tool_choice,
            metadata=self._opts.metadata,
            max_tokens=self._opts.max_tokens,
            config=self._opts.config,
            virtual_key=self._opts.virtual_key,
        )


class LLMStream(llm.LLMStream):
    def __init__(
        self,
        llm: LLM,
        *,
        client: Portkey,
        model: str | PortkeyChatModels,
        chat_ctx: llm.ChatContext,
        conn_options: APIConnectOptions,
        fnc_ctx: Optional[llm.FunctionContext],
        temperature: Optional[float],
        n: Optional[int],
        parallel_tool_calls: Optional[bool],
        tool_choice: Union[ToolChoice, Literal["auto", "required", "none"]],
        metadata: Optional[Dict[str, str]] = None,
        max_tokens: Optional[int] = None,
        config: Optional[Union[str, Dict[str, Any]]] = None,
        virtual_key: Optional[str] = None,
    ) -> None:
        super().__init__(llm=llm, chat_ctx=chat_ctx, fnc_ctx=fnc_ctx, conn_options=conn_options)
        self._client = client
        self._model = model
        self._llm: LLM = llm
        
        self._temperature = temperature
        self._n = n
        self._parallel_tool_calls = parallel_tool_calls
        self._tool_choice = tool_choice
        self._metadata = metadata
        self._max_tokens = max_tokens
        self._config = config
        self._virtual_key = virtual_key
        
        # Function call tracking
        self._function_calls_info = []
        self._tool_call_id = None
        self._fnc_name = None
        self._fnc_raw_arguments = None
        self._tool_index = None

    async def _run(self) -> None:
        # Reset state for each run/attempt
        self._tool_call_id = None
        self._fnc_name = None
        self._fnc_raw_arguments = None
        self._tool_index = None
        retryable = True

        try:
            # Prepare function descriptions if needed
            if self._fnc_ctx and len(self._fnc_ctx.ai_functions) > 0:
                tools = []
                for func in self._fnc_ctx.ai_functions.values():
                    # Create tool descriptions in the format expected by Portkey/OpenAI
                    tool = {
                        "type": "function",
                        "function": {
                            "name": func.name,
                            "description": func.description,
                            "parameters": {
                                "type": "object",
                                "properties": {},
                                "required": [],
                            }
                        }
                    }
                    
                    # Add parameters
                    for param_name, param in func.parameters.items():
                        tool["function"]["parameters"]["properties"][param_name] = {
                            "type": param.type,
                            "description": param.description
                        }
                        
                        if param.required:
                            tool["function"]["parameters"]["required"].append(param_name)
                    
                    tools.append(tool)
            else:
                tools = None

            # Prepare options for the API call
            opts: Dict[str, Any] = {}
            
            # Core parameters
            if tools is not None:
                opts["tools"] = tools
            
            if self._parallel_tool_calls is not None and tools is not None:
                opts["parallel_tool_calls"] = self._parallel_tool_calls
                
            if tools is not None:
                if isinstance(self._tool_choice, ToolChoice):
                    opts["tool_choice"] = {"type": "function", "function": {"name": self._tool_choice.name}}
                else:
                    opts["tool_choice"] = self._tool_choice
            
            if self._temperature is not None:
                opts["temperature"] = self._temperature
                
            if self._max_tokens is not None:
                opts["max_tokens"] = self._max_tokens
                
            if self._n is not None:
                opts["n"] = self._n
                
            # Stream is always true for streaming interface
            opts["stream"] = True
            
            if self._user is not None:
                opts["user"] = self._user
                
            # Add provider if specified
            if self._provider is not None:
                opts["provider"] = self._provider

            # Convert LiveKit messages to Portkey format
            messages = _build_chat_context(self._chat_ctx)
            
            # Client configuration options
            client_options = {}
            
            if self._config is not None:
                client_options["config"] = self._config
                
            if self._metadata is not None:
                client_options["metadata"] = self._metadata
                
            if self._virtual_key is not None:
                client_options["virtual_key"] = self._virtual_key
            
            # Create client with options
            client = self._client
            if client_options:
                client = client.with_options(**client_options)
                
            # Make the API call
            stream = client.chat.completions.create(
                messages=messages,
                model=self._model,
                **opts,
            )
            
            # Process streaming response
            for chunk in stream:
                for choice in chunk.choices:
                    chat_chunk = self._parse_choice(chunk.id, choice)
                    if chat_chunk is not None:
                        retryable = False
                        self._event_ch.send_nowait(chat_chunk)
                    
                # Send usage information if available
                if hasattr(chunk, "usage") and chunk.usage is not None:
                    usage = chunk.usage
                    self._event_ch.send_nowait(
                        llm.ChatChunk(
                            request_id=chunk.id,
                            usage=llm.CompletionUsage(
                                completion_tokens=usage.completion_tokens,
                                prompt_tokens=usage.prompt_tokens,
                                total_tokens=usage.total_tokens,
                            ),
                        )
                    )

        except Exception as e:
            if isinstance(e, PortkeyAPITimeoutError):
                raise APITimeoutError(retryable=retryable)
            elif isinstance(e, PortkeyAPIStatusError):
                raise APIStatusError(
                    str(e),
                    status_code=e.status_code,
                    request_id=getattr(e, 'request_id', None),
                    body=getattr(e, 'body', None),
                )
            else:
                raise APIConnectionError(retryable=retryable) from e

    def _parse_choice(self, id: str, choice: Any) -> llm.ChatChunk | None:
        delta = choice.delta

        # Handle case where delta might be None
        if delta is None:
            return None

        # Process tool calls if present
        if hasattr(delta, "tool_calls") and delta.tool_calls:
            # Check if we have functions to call
            for tool in delta.tool_calls:
                if not hasattr(tool, "function") or tool.function is None:
                    continue  # Skip if not a function tool

                # Check if we need to finalize a previous function call
                call_chunk = None
                if self._tool_call_id and hasattr(tool, "id") and tool.id and tool.index != self._tool_index:
                    call_chunk = self._try_build_function(id, choice)

                # Begin a new function call or continue an existing one
                if hasattr(tool.function, "name") and tool.function.name:
                    self._tool_index = tool.index
                    self._tool_call_id = tool.id
                    self._fnc_name = tool.function.name
                    self._fnc_raw_arguments = getattr(tool.function, "arguments", "") or ""
                elif hasattr(tool.function, "arguments") and tool.function.arguments:
                    self._fnc_raw_arguments += tool.function.arguments

                if call_chunk is not None:
                    return call_chunk

        # Finalize tool call if complete
        if hasattr(choice, "finish_reason") and choice.finish_reason in ("tool_calls", "stop") and self._tool_call_id:
            return self._try_build_function(id, choice)

        # Return regular content update
        return llm.ChatChunk(
            request_id=id,
            choices=[
                llm.Choice(
                    delta=llm.ChoiceDelta(
                        content=delta.content, 
                        role="assistant"
                    ),
                    index=choice.index,
                )
            ],
        )

    def _try_build_function(self, id: str, choice: Any) -> llm.ChatChunk | None:
        """Attempt to build a function call from the current state."""
        if not self._fnc_ctx:
            return None

        if self._tool_call_id is None or self._fnc_name is None or self._fnc_raw_arguments is None:
            return None

        # Create function call info
        fnc_info = _create_ai_function_info(
            self._fnc_ctx, 
            self._tool_call_id, 
            self._fnc_name, 
            self._fnc_raw_arguments
        )

        # Reset function call state
        self._tool_call_id = self._fnc_name = self._fnc_raw_arguments = None
        self._function_calls_info.append(fnc_info)

        # Return chunk with function call
        return llm.ChatChunk(            request_id=id,
            choices=[
                llm.Choice(
                    delta=llm.ChoiceDelta(
                        role="assistant",
                        tool_calls=[fnc_info],
                        content=getattr(choice.delta, "content", None),
                    ),
                    index=choice.index,
                )
            ],
        )
