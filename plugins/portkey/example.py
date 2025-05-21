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

import asyncio
import os
from livekit.agents import llm
from livekit.plugins.portkey import LLM

async def main():
    # Get API key from environment variable
    api_key = os.environ.get("PORTKEY_API_KEY")
    if not api_key:
        raise ValueError("PORTKEY_API_KEY environment variable is not set")
    
    # Example 1: Using OpenAI through Portkey
    portkey_llm = LLM(
        model="gpt-4o",
        api_key=api_key,
        provider="openai",  # Specify the provider
    )
    
    # Create a chat context
    chat_ctx = llm.ChatContext()
    chat_ctx.add_message(llm.ChatMessage(role="system", content="You are a helpful assistant."))
    chat_ctx.add_message(llm.ChatMessage(role="user", content="What is the capital of France?"))
    
    # Get a response
    async with portkey_llm.chat(chat_ctx=chat_ctx) as stream:
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)
    print("\n")
    
    # Example 2: Using Anthropic through Portkey
    anthropic_llm = LLM(
        model="claude-3-sonnet-20240229",
        api_key=api_key,
        provider="anthropic",  # Specify the provider
    )
    
    # Create a chat context
    chat_ctx = llm.ChatContext()
    chat_ctx.add_message(llm.ChatMessage(role="system", content="You are a helpful assistant."))
    chat_ctx.add_message(llm.ChatMessage(role="user", content="What is the capital of Germany?"))
    
    # Get a response
    async with anthropic_llm.chat(chat_ctx=chat_ctx) as stream:
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)
    print("\n")
    
    # Example 3: Using function calling with Portkey
    function_llm = LLM(
        model="gpt-4o",
        api_key=api_key,
        provider="openai",
    )
    
    # Define a function
    def get_weather(location: str, unit: str = "celsius") -> str:
        """Get the current weather in a given location"""
        # This is a mock function
        return f"The weather in {location} is 22 degrees {unit}"
    
    # Create function context
    fnc_ctx = llm.FunctionContext()
    fnc_ctx.add_function(get_weather)
    
    # Create chat context
    chat_ctx = llm.ChatContext()
    chat_ctx.add_message(llm.ChatMessage(role="system", content="You are a helpful assistant."))
    chat_ctx.add_message(llm.ChatMessage(role="user", content="What's the weather like in Paris?"))
    
    # Get a response with function calling
    async with function_llm.chat(chat_ctx=chat_ctx, fnc_ctx=fnc_ctx) as stream:
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)
            elif chunk.choices and chunk.choices[0].delta.tool_calls:
                for tool_call in chunk.choices[0].delta.tool_calls:
                    print(f"\nCalling function: {tool_call.name} with args: {tool_call.arguments}")
                    # Execute the function
                    result = fnc_ctx.execute_function(tool_call)
                    print(f"Function result: {result}")
                    
                    # Add the function result to the chat context
                    chat_ctx.add_message(
                        llm.ChatMessage(
                            role="function",
                            name=tool_call.name,
                            content=result,
                        )
                    )
                    
                    # Continue the conversation with the function result
                    async with function_llm.chat(chat_ctx=chat_ctx) as continuation:
                        async for cont_chunk in continuation:
                            if cont_chunk.choices and cont_chunk.choices[0].delta.content:
                                print(cont_chunk.choices[0].delta.content, end="", flush=True)
    print("\n")

if __name__ == "__main__":
    asyncio.run(main()) 