import os
from typing import Dict, Any, Optional, Union, List
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Config
from worker.config import get_config

# Logger
from worker.utils.logger import logger

class SlackClient:
    """
    A client for interacting with the Slack API.
    
    This service provides methods for sending messages to Slack channels
    and handles authentication, error handling, and logging.
    """
    
    _instance = None
    _slack_client = None
    
    def __new__(cls):
        """
        Create a new instance of SlackClient if one does not exist.
        
        Returns:
            SlackClient: The singleton instance
        """
        if cls._instance is None:
            cls._instance = super(SlackClient, cls).__new__(cls)
            # Initialize the slack client with token from environment
            slack_token = get_config().slack_token
            if not slack_token:
                raise ValueError("Slack token is not configured")
            cls._instance._slack_client = WebClient(token=slack_token)
        return cls._instance
    
    @classmethod
    def get_instance(cls):
        """
        Get the singleton instance of SlackClient.
        
        Returns:
            SlackClient: The singleton instance
        """
        if cls._instance is None:
            return cls()
        return cls._instance
    
    async def send_message(self, 
                          channel: str, 
                          message: str, 
                          options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send a message to a Slack channel.
        
        Args:
            channel: The Slack channel ID
            message: The message text to send
            options: Additional options (e.g., thread_ts for threaded replies)
            
        Returns:
            Dict: Response data from Slack API
            
        Raises:
            Exception: When the request fails
        """
        try:
            data: Dict[str, Any] = {
                "channel": channel,
                "text": message
            }
            
            # Add thread_ts if provided in options
            if options and "thread_ts" in options:
                data["thread_ts"] = options["thread_ts"]
                
            # Add any other options
            if options:
                for key, value in options.items():
                    if key != "thread_ts":  # Already handled above
                        data[key] = value
            
            response = self._slack_client.chat_postMessage(**data)
            
            return response
            
        except SlackApiError as error:
            logger.error(
                f"Failed to send message to Slack channel ID: {channel}, Error: {error.response['error']}"
            )
            raise Exception(f"Slack message send failed: {error.response['error']}")
    
    async def send_message_without_throw(self, 
                                       channel: str, 
                                       message: str, 
                                       options: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Send a message to a Slack channel without throwing an exception on failure.
        
        Args:
            channel: The Slack channel ID
            message: The message text to send
            options: Additional options (e.g., thread_ts for threaded replies)
            
        Returns:
            Optional[Dict]: Response data from Slack API or None on failure
        """
        try:
            return await self.send_message(channel, message, options)
        except Exception as e:
            logger.error(
                f"Failed to send message to Slack channel ID: {channel}, Error: {str(e)}"
            )
            return None
