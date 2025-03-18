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
from typing import Any, Dict, List, Literal, Optional, Union, MutableSet

import httpx
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
    user: Optional[str]
    temperature: Optional[float]
    parallel_tool_calls: Optional[bool]
    tool_choice: Union[ToolChoice, Literal["auto", "required", "none"]] = "auto"
    store: Optional[bool] = None
    metadata: Optional[Dict[str, str]] = None
    max_tokens: Optional[int] = 1024
    provider: Optional[ProviderOptions] = None
    api_base: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    virtual_key: Optional[str] = None
    trace_id: Optional[str] = None
    feedback_enabled: Optional[bool] = None
    retry_settings: Optional[Dict[str, Any]] = None
    fallbacks: Optional[list] = None
    config: Optional[Union[str, Dict[str, Any]]] = None


def _get_api_key(env_var: str, key: str | None) -> str:
    """Get API key from environment variable or provided key."""
    key = key or os.environ.get(env_var)
    if not key:
        raise ValueError(
            f"{env_var} is required, either as argument or set {env_var} environmental variable"
        )
    return key


def _strip_nones(data: dict[str, Any]) -> dict[str, Any]:
    """Remove None values from dictionary."""
    return {k: v for k, v in data.items() if v is not None}


def build_oai_function_description(func: llm.AIFunction, capabilities: llm.LLMCapabilities) -> Dict[str, Any]:
    """Build OpenAI compatible function description."""
    params = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    for param in func.parameters:
        params["properties"][param.name] = {"type": param.type}
        if param.description:
            params["properties"][param.name]["description"] = param.description
        if param.required:
            params["required"].append(param.name)
        if param.enum:
            params["properties"][param.name]["enum"] = param.enum

    return {
        "type": "function",
        "function": {
            "name": func.name,
            "description": func.description,
            "parameters": params,
        },
    }


def _build_oai_context(chat_ctx: llm.ChatContext, cache_key: Any) -> List[Dict[str, Any]]:
    """Build OpenAI compatible message list from ChatContext."""
    messages = []
    for msg in chat_ctx.messages:
        if msg.role == "system":
            messages.append({"role": "system", "content": msg.content})
        elif msg.role == "user":
            messages.append({"role": "user", "content": msg.content})
        elif msg.role == "assistant":
            if msg.tool_calls and len(msg.tool_calls) > 0:
                assistant_msg = {"role": "assistant", "content": msg.content}
                tool_calls = []
                for tool_call in msg.tool_calls:
                    tool_calls.append({
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.name,
                            "arguments": tool_call.arguments,
                        }
                    })
                assistant_msg["tool_calls"] = tool_calls
                messages.append(assistant_msg)
            else:
                messages.append({"role": "assistant", "content": msg.content})
        elif msg.role == "tool":
            messages.append({
                "role": "tool",
                "tool_call_id": msg.tool_call_id,
                "content": msg.content,
            })
    return messages


class LLM(llm.LLM):
    def __init__(
        self,
        *,
        model: str | PortkeyChatModels = "gpt-4o",
        api_key: Optional[str] = None,
        user: Optional[str] = None,
        temperature: Optional[float] = None,
        parallel_tool_calls: Optional[bool] = None,
        tool_choice: Union[ToolChoice, Literal["auto", "required", "none"]] = "auto",
        store: Optional[bool] = None,
        metadata: Optional[Dict[str, str]] = None,
        max_tokens: Optional[int] = 1024,
        provider: Optional[ProviderOptions] = None,
        api_base: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        virtual_key: Optional[str] = None,
        trace_id: Optional[str] = None,
        feedback_enabled: Optional[bool] = None,
        retry_settings: Optional[Dict[str, Any]] = None,
        fallbacks: Optional[list] = None,
        config: Optional[Union[str, Dict[str, Any]]] = None,
    ) -> None:
        """
        Create a new instance of Portkey LLM.

        ``api_key`` must be set to your Portkey API key, either using the argument or by setting the
        ``PORTKEY_API_KEY`` environmental variable.
        
        Parameters:
            model: The model to use for generating completions.
            api_key: Your Portkey API key.
            user: A unique identifier representing your end-user.
            temperature: Controls randomness. Higher values mean more random completions.
            parallel_tool_calls: Whether to allow parallel function calls.
            tool_choice: Controls which function is called by the model.
            store: Whether to store the request and response in Portkey.
            metadata: Additional metadata to include with the request (will be converted to JSON).
            max_tokens: The maximum number of tokens to generate.
            provider: The provider to use (e.g., "openai", "anthropic", etc.).
            api_base: The base URL for the Portkey API.
            headers: Additional headers to include with the request.
            virtual_key: A virtual key to use for the request.
            trace_id: A trace ID to associate with the request.
            feedback_enabled: Whether to enable feedback for the request.
            retry_settings: Settings for retrying failed requests.
            fallbacks: A list of fallback configurations.
            config: A Portkey config string ID (e.g., "pc-xxxx") or a config dictionary.
        """
        super().__init__(
            capabilities=LLMCapabilities(
                supports_choices_on_int=True,
                requires_persistent_functions=False,
            )
        )

        self._opts = LLMOptions(
            model=model,
            user=user,
            temperature=temperature,
            parallel_tool_calls=parallel_tool_calls,
            tool_choice=tool_choice,
            store=store,
            metadata=metadata,
            max_tokens=max_tokens,
            provider=provider,
            api_base=api_base,
            headers=headers,
            virtual_key=virtual_key,
            trace_id=trace_id,
            feedback_enabled=feedback_enabled,
            retry_settings=retry_settings,
            fallbacks=fallbacks,
            config=config,
        )
        
        api_key = _get_api_key("PORTKEY_API_KEY", api_key)
        
        # Initialize Portkey client
        self._client = Portkey(
            api_key=api_key,
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
            user=self._opts.user,
            chat_ctx=chat_ctx,
            fnc_ctx=fnc_ctx,
            conn_options=conn_options,
            n=n,
            temperature=temperature,
            parallel_tool_calls=parallel_tool_calls,
            tool_choice=tool_choice,
            provider=self._opts.provider,
        )


class LLMStream(llm.LLMStream):
    def __init__(
        self,
        llm: LLM,
        *,
        client: Portkey,
        model: str | PortkeyChatModels,
        user: Optional[str],
        chat_ctx: llm.ChatContext,
        conn_options: APIConnectOptions,
        fnc_ctx: Optional[llm.FunctionContext],
        temperature: Optional[float],
        n: Optional[int],
        parallel_tool_calls: Optional[bool],
        tool_choice: Union[ToolChoice, Literal["auto", "required", "none"]],
        provider: Optional[ProviderOptions] = None,
    ) -> None:
        super().__init__(
            llm, chat_ctx=chat_ctx, fnc_ctx=fnc_ctx, conn_options=conn_options
        )
        self._client = client
        self._model = model
        self._llm: LLM = llm

        self._user = user
        self._temperature = temperature
        self._n = n
        self._parallel_tool_calls = parallel_tool_calls
        self._tool_choice = tool_choice
        self._provider = provider
        
        # Function call tracking
        self._tool_call_id = None
        self._fnc_name = None
        self._fnc_raw_arguments = None
        self._tool_index = None
        self._function_calls_info = []

    def _parse_choice(self, id: str, choice: Any) -> llm.ChatChunk | None:
        delta = choice.delta

        # Handle null delta
        if delta is None:
            return None

        if delta.tool_calls:
            # check if we have functions to calls
            for tool in delta.tool_calls:
                if not tool.function:
                    continue  # may add other tools in the future

                call_chunk = None
                if self._tool_call_id and tool.id and tool.index != self._tool_index:
                    call_chunk = self._try_build_function(id, choice)

                if tool.function.name:
                    self._tool_index = tool.index
                    self._tool_call_id = tool.id
                    self._fnc_name = tool.function.name
                    self._fnc_raw_arguments = tool.function.arguments or ""
                elif tool.function.arguments:
                    self._fnc_raw_arguments += tool.function.arguments  # type: ignore

                if call_chunk is not None:
                    return call_chunk

        if choice.finish_reason in ("tool_calls", "stop") and self._tool_call_id:
            # we're done with the tool calls, run the last one
            return self._try_build_function(id, choice)

        return llm.ChatChunk(
            request_id=id,
            choices=[
                llm.Choice(
                    delta=llm.ChoiceDelta(content=delta.content, role="assistant"),
                    index=choice.index,
                )
            ],
        )

    def _try_build_function(self, id: str, choice: Any) -> llm.ChatChunk | None:
        if not self._fnc_ctx:
            return None

        if self._tool_call_id is None:
            return None

        if self._fnc_name is None or self._fnc_raw_arguments is None:
            return None

        fnc_info = _create_ai_function_info(
            self._fnc_ctx, self._tool_call_id, self._fnc_name, self._fnc_raw_arguments
        )

        self._tool_call_id = self._fnc_name = self._fnc_raw_arguments = None
        self._function_calls_info.append(fnc_info)

        return llm.ChatChunk(
            request_id=id,
            choices=[
                llm.Choice(
                    delta=llm.ChoiceDelta(
                        role="assistant",
                        tool_calls=[fnc_info],
                        content=choice.delta.content,
                    ),
                    index=choice.index,
                )
            ],
        )

    async def _run(self) -> None:
        # Reset tracking variables to ensure fresh state for each run/attempt
        self._tool_call_id = None
        self._fnc_name = None
        self._fnc_raw_arguments = None
        self._tool_index = None
        retryable = True

        try:
            if self._fnc_ctx and len(self._fnc_ctx.ai_functions) > 0:
                tools = [
                    build_oai_function_description(fnc, self._llm._capabilities)
                    for fnc in self._fnc_ctx.ai_functions.values()
                ]
            else:
                tools = None

            opts: Dict[str, Any] = {
                "tools": tools,
                "parallel_tool_calls": self._parallel_tool_calls if tools else None,
                "tool_choice": (
                    {"type": "function", "function": {"name": self._tool_choice.name}}
                    if isinstance(self._tool_choice, ToolChoice)
                    else self._tool_choice
                )
                if tools is not None
                else None,
                "temperature": self._temperature,
                "max_tokens": self._llm._opts.max_tokens,
                "n": self._n,
                "stream": True,
                "user": self._user or None,
            }
            
            # Add provider if specified
            if self._provider:
                opts["provider"] = self._provider
                
            # remove None values from the options
            opts = _strip_nones(opts)

            messages = _build_oai_context(self._chat_ctx, id(self))
            
            # Prepare with_options parameters
            with_options_params = {}
            if self._llm._opts.metadata is not None:
                with_options_params["metadata"] = self._llm._opts.metadata
            if self._llm._opts.config is not None:
                with_options_params["config"] = self._llm._opts.config

            print(f"with_options_params: {with_options_params}")
            print(f"opts: {opts}")
            client = self._client.with_options(**with_options_params)
            stream = client.chat.completions.create(
                messages=messages,
                model=self._model,
                **opts,
            )
            for chunk in stream:
                for choice in chunk.choices:
                    chat_chunk = self._parse_choice(chunk.id, choice)
                    if chat_chunk is not None:
                        retryable = False
                        self._event_ch.send_nowait(chat_chunk)
                    if chunk.usage is not None:
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
