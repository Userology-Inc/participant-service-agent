import os
from typing import Dict, Any, Optional
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Config
from dotenv import load_dotenv

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("slack")

# Load environment variables
load_dotenv()

class SlackClient:
    """Singleton class for Slack client"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SlackClient, cls).__new__(cls)
            # Initialize the slack client with token from environment
            slack_token = os.getenv("SLACK_TOKEN")
            if not slack_token:
                raise ValueError("SLACK_TOKEN environment variable is not set")
            cls._instance.slack_client = WebClient(token=slack_token)
        return cls._instance

    @classmethod
    def get_instance(cls):
        """Get singleton instance of SlackClient"""
        if cls._instance is None:
            return cls()
        return cls._instance

    async def send_message(
        self, 
        slack_channel: str, 
        message: str, 
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send a message to a Slack channel
        
        Args:
            slack_channel: The Slack channel ID to send the message to
            message: The message text to send
            options: Additional options like thread_ts for threading
            
        Returns:
            The Slack API response
            
        Raises:
            Exception: If the message fails to send
        """
        try:
            data: Dict[str, Any] = {
                "channel": slack_channel,
                "text": message,
            }

            if options and "thread_ts" in options:
                data["thread_ts"] = options["thread_ts"]

            response = self.slack_client.chat_postMessage(**data)
            return response
        except SlackApiError as error:
            # Log the error
            logger.error(
                f"Failed to send message to Slack channel Id: {slack_channel}, Error: {error.response['error']}"
            )
            # Rethrow the error
            raise Exception(f"Slack message send failed: {error.response['error']}")
