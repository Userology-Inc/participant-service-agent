#!/usr/bin/env python3
"""
Simple test script for slack_sdk integration.
"""

import os
import unittest
import pytest
from unittest.mock import patch, MagicMock
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Import our SlackClient implementation
from worker.services.slack.client import SlackClient

class TestSlackSDKIntegration(unittest.TestCase):
    """Tests for the SlackClient class using slack_sdk."""
    
    @patch('worker.services.slack.client.get_config')
    def test_client_initialization(self, mock_get_config):
        """Test that the SlackClient initializes the WebClient correctly."""
        # Setup mock config
        config_mock = MagicMock()
        config_mock.slack_token = "xoxb-test-token"
        mock_get_config.return_value = config_mock
        
        # Reset singleton for testing
        SlackClient._instance = None
        
        # Initialize slack client
        with patch('worker.services.slack.client.WebClient') as mock_webclient:
            client = SlackClient()
            mock_webclient.assert_called_once_with(token="xoxb-test-token")
    
    @patch('worker.services.slack.client.get_config')
    def test_get_instance_returns_same_instance(self, mock_get_config):
        """Test that get_instance returns the same singleton instance."""
        # Setup mock config
        config_mock = MagicMock()
        config_mock.slack_token = "xoxb-test-token"
        mock_get_config.return_value = config_mock
        
        # Reset singleton for testing
        SlackClient._instance = None
        
        # Get two instances
        with patch('worker.services.slack.client.WebClient'):
            instance1 = SlackClient.get_instance()
            instance2 = SlackClient.get_instance()
            
            # They should be the same object
            self.assertIs(instance1, instance2)

    @pytest.mark.asyncio
    @patch('worker.services.slack.client.get_config')
    async def test_send_message(self, mock_get_config):
        """Test sending a message."""
        # Setup mock config
        config_mock = MagicMock()
        config_mock.slack_token = "xoxb-test-token"
        mock_get_config.return_value = config_mock
        
        # Reset singleton for testing
        SlackClient._instance = None
        
        # Create a mock webclient
        mock_webclient = MagicMock()
        mock_response = {
            "ok": True,
            "channel": "C1234567890",
            "ts": "1234567890.123456"
        }
        mock_webclient.chat_postMessage.return_value = mock_response
        
        # Initialize slack client with mock webclient
        with patch('worker.services.slack.client.WebClient', return_value=mock_webclient):
            client = SlackClient.get_instance()
            response = await client.send_message("C1234567890", "Hello, world!")
            
            # Check the webclient was called correctly
            mock_webclient.chat_postMessage.assert_called_once_with(
                channel="C1234567890",
                text="Hello, world!"
            )
            
            # Check we got the expected response
            self.assertEqual(response, mock_response)
    
    @pytest.mark.asyncio
    @patch('worker.services.slack.client.get_config')
    async def test_send_message_error_handling(self, mock_get_config):
        """Test error handling when sending a message."""
        # Setup mock config
        config_mock = MagicMock()
        config_mock.slack_token = "xoxb-test-token"
        mock_get_config.return_value = config_mock
        
        # Reset singleton for testing
        SlackClient._instance = None
        
        # Create a mock webclient with error response
        mock_webclient = MagicMock()
        error_response = {"error": "channel_not_found"}
        mock_error = SlackApiError("Error sending message", error_response)
        mock_webclient.chat_postMessage.side_effect = mock_error
        
        # Initialize slack client with mock webclient
        with patch('worker.services.slack.client.WebClient', return_value=mock_webclient):
            client = SlackClient.get_instance()
            
            # Test send_message (should raise exception)
            with self.assertRaises(Exception) as context:
                await client.send_message("C1234567890", "Hello, world!")
            self.assertIn("channel_not_found", str(context.exception))
            
            # Test send_message_without_throw (should return None)
            response = await client.send_message_without_throw("C1234567890", "Hello, world!")
            self.assertIsNone(response)

if __name__ == "__main__":
    unittest.main() 