# Slack Service

This service provides a Python implementation of a Slack client for sending messages to Slack channels.

## Installation

Install the required dependencies:

```bash
pip3 install slack-sdk python-dotenv
```

## Configuration

Create a `.env` file in the root directory of your project with the following variables:

```
SLACK_TOKEN=xoxb-your-slack-bot-token
SLACK_CHANNEL_ID=C0123456789
```

You can obtain a Slack Bot Token by:

1. Going to https://api.slack.com/apps
2. Creating a new app or selecting an existing one
3. Navigate to "OAuth & Permissions"
4. Add the following scopes:
   - `chat:write`
   - `chat:write.public`
5. Install the app to your workspace
6. Copy the "Bot User OAuth Token" that starts with `xoxb-`

## Usage

```python
import asyncio
from worker.services.slack import SlackClient

async def send_slack_notification():
    # Get the Slack client instance
    slack_client = SlackClient.get_instance()

    # Send a message
    response = await slack_client.send_message(
        slack_channel="your-channel-id",
        message="Hello from the Slack service!"
    )

    # Send a threaded reply
    thread_ts = response.get("ts")
    await slack_client.send_message(
        slack_channel="your-channel-id",
        message="This is a threaded reply!",
        options={"thread_ts": thread_ts}
    )

# Run the async function
asyncio.run(send_slack_notification())
```

## Features

- Singleton pattern for efficient client reuse
- Async support for non-blocking operations
- Error handling with detailed logging
- Support for threaded messages
- Environment variable configuration
