"""
Slack service module for interacting with the Slack API.

This module provides a client for sending messages to Slack channels.
"""

from worker.services.slack.client import SlackClient

__all__ = [
    'SlackClient'
]
