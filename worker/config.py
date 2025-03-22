#!/usr/bin/env python3
"""
Configuration management for the participant service agent.
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@dataclass
class Config:
    """Configuration class for the worker service."""
    # LiveKit configuration
    livekit_url: str
    livekit_api_key: str
    livekit_api_secret: str
    livekit_trunk_id: str
    
    # API Keys
    openai_api_key: str
    eleven_api_key: str
    elevenlabs_api_key: str
    deepgram_api_key: str
    portkey_api_key: str
    sarvam_api_key: str
    
    # Database
    db_service_url: str
    
    # AWS
    aws_secret_access_key: str
    aws_access_key_id: str
    aws_region: str
    
    # Slack
    slack_token: str
    slack_channel_id: str
    
    # Logging
    log_level: str = "INFO"

def get_config() -> Config:
    """Load configuration from environment variables."""
    return Config(
        # LiveKit configuration
        livekit_url=os.getenv("LIVEKIT_URL", ""),
        livekit_api_key=os.getenv("LIVEKIT_API_KEY", ""),
        livekit_api_secret=os.getenv("LIVEKIT_API_SECRET", ""),
        livekit_trunk_id=os.getenv("LIVEKIT_TRUNK_ID", ""),
        
        # API Keys
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        eleven_api_key=os.getenv("ELEVEN_API_KEY", ""),
        elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY", ""),
        deepgram_api_key=os.getenv("DEEPGRAM_API_KEY", ""),
        portkey_api_key=os.getenv("PORTKEY_API_KEY", ""),
        sarvam_api_key=os.getenv("SARVAM_API_KEY", ""),
        
        # Database
        db_service_url=os.getenv("DB_SERVICE_URL", ""),
        
        # AWS
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", ""),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", ""),
        aws_region=os.getenv("AWS_REGION", ""),
        
        # Slack
        slack_token=os.getenv("SLACK_TOKEN", ""),
        slack_channel_id=os.getenv("SLACK_CHANNEL_ID", ""),
        
        # Logging
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    ) 