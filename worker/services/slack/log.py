import logging
import json
from typing import Dict, Any

# Set up logger
logger = logging.getLogger("slack_service")

def setup_logger(log_level: str = "INFO"):
    """
    Set up the Slack service logger with the specified log level.
    
    Args:
        log_level: The log level to use (default: INFO)
        
    Returns:
        logging.Logger: The configured logger
    """
    # Get the integer log level from the string
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure logger
    logger.setLevel(level)
    
    # Add handler if there are none
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger

def log_request(method: str, url: str, data: Any = None):
    """
    Log a request to the Slack API.
    
    Args:
        method: The HTTP method used
        url: The URL called
        data: The request data (if any)
    """
    message = f"Slack API Request: {method} {url}"
    
    # Format JSON data for logging, but mask the token
    if data:
        if isinstance(data, dict):
            # Create a copy to avoid modifying the original
            log_data = data.copy()
            
            # Mask sensitive data if present
            if "token" in log_data:
                log_data["token"] = "********"
            
            message += f" Data: {json.dumps(log_data)}"
    
    logger.info(message)

def log_response(method: str, url: str, status_code: int, data: Any = None, duration_ms: float = 0):
    """
    Log a response from the Slack API.
    
    Args:
        method: The HTTP method used
        url: The URL called
        status_code: The HTTP status code
        data: The response data (if any)
        duration_ms: Request duration in milliseconds
    """
    message = f"Slack API Response: {method} {url} Status: {status_code} Duration: {duration_ms:.2f}ms"
    
    # Log response data if present
    if data:
        message += f" Data: {json.dumps(data)}"
    
    logger.info(message)

def log_error(error_type: str, status_code: int, method: str, url: str, error_message: str, duration_ms: float = 0):
    """
    Log an error from the Slack API.
    
    Args:
        error_type: The type of error
        status_code: The HTTP status code (if any)
        method: The HTTP method used
        url: The URL called
        error_message: The error message
        duration_ms: Request duration in milliseconds
    """
    status_part = f" Status: {status_code}" if status_code else ""
    message = f"Slack API Error: {error_type}{status_part} {method} {url} Duration: {duration_ms:.2f}ms Error: {error_message}"
    logger.error(message)

# Initialize logger with default settings
setup_logger()
