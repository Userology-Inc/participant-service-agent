import pytest
import unittest.mock as mock
from unittest.mock import MagicMock, patch
import json

from worker.services.slack.client import SlackClient
from slack_sdk.errors import SlackApiError


class TestSlackClient:
    """Test cases for the SlackClient class."""

    @pytest.fixture
    def mock_config(self):
        """Mock the config to return test values."""
        with patch('worker.services.slack.client.get_config') as mock_get_config:
            config_mock = MagicMock()
            config_mock.slack_token = "test-token"
            mock_get_config.return_value = config_mock
            yield mock_get_config

    @pytest.fixture
    def mock_webclient(self):
        """Mock the WebClient."""
        with patch('worker.services.slack.client.WebClient') as mock_webclient_class:
            webclient_mock = MagicMock()
            mock_webclient_class.return_value = webclient_mock
            yield webclient_mock

    def test_get_instance(self):
        """Test that get_instance returns a singleton instance."""
        # Reset the singleton instance for testing
        SlackClient._instance = None
        instance1 = SlackClient.get_instance()
        instance2 = SlackClient.get_instance()
        
        assert instance1 is instance2
        assert isinstance(instance1, SlackClient)

    def test_new_client_initialization(self, mock_config, mock_webclient):
        """Test that __new__ initializes the WebClient correctly."""
        # Reset the instance for testing
        SlackClient._instance = None
        
        # Get a new client instance
        client = SlackClient()
        
        # Verify that the WebClient was created with the correct token
        from worker.services.slack.client import WebClient
        WebClient.assert_called_once_with(token="test-token")

    @pytest.mark.asyncio
    async def test_send_message_success(self, mock_config, mock_webclient):
        """Test successful message sending."""
        # Configure the mock response
        mock_response = {
            "ok": True,
            "channel": "C1234567890",
            "ts": "1234567890.123456",
            "message": {
                "text": "Test message"
            }
        }
        mock_webclient.chat_postMessage.return_value = mock_response
        
        # Reset the singleton instance for testing
        SlackClient._instance = None
        SlackClient._slack_client = None
        
        # Get a client instance
        client = SlackClient.get_instance()
        # Manually set the _slack_client to use our mock
        client._slack_client = mock_webclient
        
        # Send a message
        response = await client.send_message("C1234567890", "Test message")
        
        # Check that the client made the correct request
        mock_webclient.chat_postMessage.assert_called_once_with(
            channel="C1234567890", 
            text="Test message"
        )
        
        # Check that we got the expected response
        assert response["ok"] is True
        assert response["channel"] == "C1234567890"

    @pytest.mark.asyncio
    async def test_send_message_with_thread(self, mock_config, mock_webclient):
        """Test sending a message in a thread."""
        # Configure the mock response
        mock_response = {
            "ok": True,
            "channel": "C1234567890",
            "ts": "1234567890.123456",
            "message": {
                "text": "Test reply",
                "thread_ts": "1234567890.123000"
            }
        }
        mock_webclient.chat_postMessage.return_value = mock_response
        
        # Reset the singleton instance for testing
        SlackClient._instance = None
        SlackClient._slack_client = None
        
        # Get a client instance
        client = SlackClient.get_instance()
        # Manually set the _slack_client to use our mock
        client._slack_client = mock_webclient
        
        # Send a message in a thread
        response = await client.send_message(
            "C1234567890", 
            "Test reply", 
            {"thread_ts": "1234567890.123000"}
        )
        
        # Check that the client made the correct request
        mock_webclient.chat_postMessage.assert_called_once_with(
            channel="C1234567890", 
            text="Test reply", 
            thread_ts="1234567890.123000"
        )
        
        # Check that we got the expected response
        assert response["ok"] is True
        assert response["message"]["thread_ts"] == "1234567890.123000"

    @pytest.mark.asyncio
    async def test_send_message_with_other_options(self, mock_config, mock_webclient):
        """Test sending a message with additional options."""
        # Configure the mock response
        mock_response = {
            "ok": True,
            "channel": "C1234567890",
            "ts": "1234567890.123456"
        }
        mock_webclient.chat_postMessage.return_value = mock_response
        
        # Reset the singleton instance for testing
        SlackClient._instance = None
        SlackClient._slack_client = None
        
        # Get a client instance
        client = SlackClient.get_instance()
        # Manually set the _slack_client to use our mock
        client._slack_client = mock_webclient
        
        # Send a message with additional options
        response = await client.send_message(
            "C1234567890", 
            "Test message", 
            {"unfurl_links": False, "parse": "none"}
        )
        
        # Check that the client made the correct request with all options
        mock_webclient.chat_postMessage.assert_called_once_with(
            channel="C1234567890", 
            text="Test message",
            unfurl_links=False,
            parse="none"
        )
        
        # Check that we got the expected response
        assert response["ok"] is True

    @pytest.mark.asyncio
    async def test_send_message_error(self, mock_config, mock_webclient):
        """Test handling of API errors."""
        # Configure the mock to raise a SlackApiError
        error_response = {"error": "channel_not_found"}
        mock_error = SlackApiError("Error message", error_response)
        mock_webclient.chat_postMessage.side_effect = mock_error
        
        # Reset the singleton instance for testing
        SlackClient._instance = None
        SlackClient._slack_client = None
        
        # Get a client instance
        client = SlackClient.get_instance()
        # Manually set the _slack_client to use our mock
        client._slack_client = mock_webclient
        
        # Try to send a message and expect it to raise an exception
        with pytest.raises(Exception) as excinfo:
            await client.send_message("invalid-channel", "Test message")
        
        # Check that the exception contains the error message
        assert "channel_not_found" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_send_message_without_throw_success(self, mock_config, mock_webclient):
        """Test successful message sending with the non-throwing method."""
        # Configure the mock response
        mock_response = {
            "ok": True,
            "channel": "C1234567890",
            "ts": "1234567890.123456",
            "message": {
                "text": "Test message"
            }
        }
        mock_webclient.chat_postMessage.return_value = mock_response
        
        # Reset the singleton instance for testing
        SlackClient._instance = None
        SlackClient._slack_client = None
        
        # Get a client instance
        client = SlackClient.get_instance()
        # Manually set the _slack_client to use our mock
        client._slack_client = mock_webclient
        
        # Send a message
        response = await client.send_message_without_throw("C1234567890", "Test message")
        
        # Check that we got the expected response
        assert response["ok"] is True
        assert response["channel"] == "C1234567890"

    @pytest.mark.asyncio
    async def test_send_message_without_throw_error(self, mock_config, mock_webclient):
        """Test that send_message_without_throw handles errors gracefully."""
        # Configure the mock to raise a SlackApiError
        error_response = {"error": "channel_not_found"}
        mock_error = SlackApiError("Error message", error_response)
        mock_webclient.chat_postMessage.side_effect = mock_error
        
        # Reset the singleton instance for testing
        SlackClient._instance = None
        SlackClient._slack_client = None
        
        # Get a client instance
        client = SlackClient.get_instance()
        # Manually set the _slack_client to use our mock
        client._slack_client = mock_webclient
        
        # Send a message with the non-throwing method
        response = await client.send_message_without_throw("invalid-channel", "Test message")
        
        # The method should return None instead of raising an exception
        assert response is None 