#!/usr/bin/env python3
"""
Example script showing how to use the SlackClient to send messages.
"""

import asyncio
import os
from dotenv import load_dotenv

from worker.services.slack import SlackClient
from worker.utils.logger import logger

# Load environment variables
load_dotenv()

async def main():
    """Run the example."""
    # Get the Slack client instance
    slack = SlackClient.get_instance()
    
    # Get channel ID from environment or use a default
    channel_id = os.getenv("SLACK_CHANNEL_ID", "your-channel-id")
    
    # Send a simple message
    logger.info(f"Sending message to channel {channel_id}")
    response = await slack.send_message(
        channel_id,
        "Hello from the SlackClient SDK example!"
    )
    logger.info(f"Message sent successfully: {response['ts']}")
    
    # Send a message in a thread (as a reply to the first message)
    thread_ts = response['ts']
    logger.info(f"Sending reply to thread {thread_ts}")
    thread_response = await slack.send_message(
        channel_id,
        "This is a threaded reply using slack_sdk!",
        {"thread_ts": thread_ts}
    )
    logger.info(f"Reply sent successfully: {thread_response['ts']}")
    
    # Demonstrate error handling with non-throwing method
    logger.info("Sending to invalid channel to demonstrate error handling")
    result = await slack.send_message_without_throw(
        "invalid-channel-id",
        "This message should fail gracefully"
    )
    
    if result is None:
        logger.info("Message failed as expected, but error was handled")
    else:
        logger.error("Message unexpectedly succeeded")

if __name__ == "__main__":
    asyncio.run(main()) 