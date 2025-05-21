# LiveKit Portkey LLM Plugin

This plugin integrates [Portkey](https://portkey.ai/) with LiveKit's LLM framework. Portkey is an AI Gateway that provides unified access to various LLM providers including OpenAI, Anthropic, Cohere, Mistral, Google, and more.

## Installation

```bash
pip install livekit-plugins-portkey
```

This will install the LiveKit Portkey plugin along with its dependencies.

## Dependencies

- `portkey-ai`: The official Portkey Python client
- `livekit-plugins-openai`: The LiveKit OpenAI plugin (used as a base for the Portkey implementation)

## Usage

### Basic Usage

```python
import os
from livekit.agents import llm
from livekit.plugins.portkey import LLM

# Initialize the Portkey LLM
portkey_llm = LLM(
    model="gpt-4o",  # The model to use
    api_key=os.environ.get("PORTKEY_API_KEY"),  # Your Portkey API key
    provider="openai",  # The provider to use (optional)
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
```

### Using Different Providers

Portkey allows you to switch between different LLM providers easily:

```python
# Using Anthropic through Portkey
anthropic_llm = LLM(
    model="claude-3-sonnet-20240229",
    api_key=os.environ.get("PORTKEY_API_KEY"),
    provider="anthropic",
)

# Using Mistral through Portkey
mistral_llm = LLM(
    model="mistral-large-latest",
    api_key=os.environ.get("PORTKEY_API_KEY"),
    provider="mistral",
)
```

### Function Calling

Portkey supports function calling with compatible models:

```python
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
chat_ctx.add_message(llm.ChatMessage(role="user", content="What's the weather like in Paris?"))

# Get a response with function calling
async with portkey_llm.chat(chat_ctx=chat_ctx, fnc_ctx=fnc_ctx) as stream:
    # Process the response...
```

### Advanced Configuration

Portkey provides additional configuration options:

```python
portkey_llm = LLM(
    model="gpt-4o",
    api_key=os.environ.get("PORTKEY_API_KEY"),
    provider="openai",
    temperature=0.7,
    max_tokens=1000,
    virtual_key="your-virtual-key",  # Portkey virtual key
    trace_id="custom-trace-id",  # Custom trace ID for tracking
    feedback_enabled=True,  # Enable feedback
    retry_settings={  # Custom retry settings
        "max_retries": 3,
        "initial_retry_delay": 1,
        "max_retry_delay": 10,
        "retry_multiplier": 2,
    },
    fallbacks=[  # Fallback configuration
        {"provider": "anthropic", "model": "claude-3-sonnet-20240229"},
        {"provider": "mistral", "model": "mistral-large-latest"},
    ],
)
```

## Available Models

The plugin supports various models from different providers:

- OpenAI: `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `gpt-4`, `gpt-3.5-turbo`
- Anthropic: `claude-3-opus-20240229`, `claude-3-sonnet-20240229`, `claude-3-haiku-20240307`, etc.
- Cohere: `command-r`, `command-r-plus`, `command`
- Mistral: `mistral-large-latest`, `mistral-medium-latest`, `mistral-small-latest`, etc.
- Google: `gemini-1.0-pro`, `gemini-1.5-pro`, `gemini-1.5-flash`
- Meta: `llama-3-70b-instruct`, `llama-3-8b-instruct`

## Provider Options

The following provider options are available:

- `openai`: OpenAI models
- `anthropic`: Anthropic models
- `cohere`: Cohere models
- `mistral`: Mistral models
- `google`: Google models
- `meta`: Meta models

## License

Apache License 2.0 