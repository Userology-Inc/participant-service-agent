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

from typing import Literal

# Portkey supports multiple providers, so we define common models for each provider
# These are just examples, Portkey can work with any model from these providers

# OpenAI models
OpenAIChatModels = Literal[
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-4",
    "gpt-3.5-turbo",
]

# Anthropic models
AnthropicChatModels = Literal[
    "claude-3-opus-20240229",
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307",
    "claude-2.1",
    "claude-2.0",
    "claude-instant-1.2",
]

# Cohere models
CohereChatModels = Literal[
    "command-r",
    "command-r-plus",
    "command",
]

# Mistral models
MistralChatModels = Literal[
    "mistral-large-latest",
    "mistral-medium-latest",
    "mistral-small-latest",
    "mistral-tiny-latest",
]

# Google models
GoogleChatModels = Literal[
    "gemini-1.0-pro",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
]

# Meta models
MetaChatModels = Literal[
    "llama-3-70b-instruct",
    "llama-3-8b-instruct",
]

# Provider literals
ProviderOptions = Literal[
    "openai",
    "anthropic",
    "cohere",
    "mistral",
    "google",
    "meta",
]

# Combined model types
PortkeyChatModels = Literal[
    OpenAIChatModels,
    AnthropicChatModels,
    CohereChatModels,
    MistralChatModels,
    GoogleChatModels,
    MetaChatModels,
] 