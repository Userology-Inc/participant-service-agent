#!/usr/bin/env python3
"""
Pytest configuration and fixtures for the test suite.
"""

import os
import pytest
from unittest.mock import MagicMock, patch
import sys

# Add parent directory to path to allow importing from the worker package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def mock_config():
    """Fixture providing a mock configuration."""
    from config import Config
    
    return Config(
        # LiveKit configuration
        livekit_url="wss://test.livekit.cloud",
        livekit_api_key="test_api_key",
        livekit_api_secret="test_api_secret",
        livekit_trunk_id="test_trunk_id",
        
        # API Keys
        openai_api_key="test_openai_key",
        eleven_api_key="test_eleven_key",
        elevenlabs_api_key="test_elevenlabs_key",
        deepgram_api_key="test_deepgram_key",
        portkey_api_key="test_portkey_key",
        sarvam_api_key="test_sarvam_key",
        
        # Database
        db_service_url="https://test.userology.info/db",
        
        # AWS
        aws_secret_access_key="test_aws_secret",
        aws_access_key_id="test_aws_key_id",
        aws_region="us-west-2",
        
        # Slack
        slack_token="test_slack_token",
        slack_channel_id="test_channel_id",
        
        # Logging
        log_level="INFO",
    )

@pytest.fixture
def mock_logger():
    """Fixture providing a mock logger."""
    with patch('utils.logger.logger') as mock:
        yield mock 