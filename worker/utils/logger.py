#!/usr/bin/env python3
"""
Logging configuration for the participant service agent.
"""

import os
import logging
import logging.handlers
from datetime import datetime
import json
from typing import Dict, Any

# Get log level from environment or use INFO as default
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_DIR = os.getenv("LOG_DIR", "logs")

# Ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

# Configure root logger
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Create logger
logger = logging.getLogger("participant-service")
logger.setLevel(getattr(logging, LOG_LEVEL))

# Clear existing handlers
if logger.handlers:
    logger.handlers.clear()

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(getattr(logging, LOG_LEVEL))
console_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_format)
logger.addHandler(console_handler)

# File handler with rotation
log_filename = os.path.join(LOG_DIR, f"worker_{datetime.now().strftime('%Y-%m-%d')}.log")
file_handler = logging.handlers.RotatingFileHandler(
    log_filename,
    maxBytes=10485760,  # 10MB
    backupCount=10
)
file_handler.setLevel(getattr(logging, LOG_LEVEL))
file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_format)
logger.addHandler(file_handler)

class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        
        if hasattr(record, "data") and isinstance(record.data, dict):
            log_data.update(record.data)
            
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_data)

# JSON file handler for structured logging
json_filename = os.path.join(LOG_DIR, f"worker_json_{datetime.now().strftime('%Y-%m-%d')}.log")
json_handler = logging.handlers.RotatingFileHandler(
    json_filename,
    maxBytes=10485760,  # 10MB
    backupCount=10
)
json_handler.setLevel(getattr(logging, LOG_LEVEL))
json_handler.setFormatter(JsonFormatter())
logger.addHandler(json_handler)

def log_with_context(level: str, message: str, **context):
    """Log a message with additional context data."""
    record = logging.LogRecord(
        name=logger.name,
        level=getattr(logging, level.upper()),
        pathname=__file__,
        lineno=0,
        msg=message,
        args=(),
        exc_info=None
    )
    record.data = context
    logger.handle(record)

# Add convenience methods
logger.debug_with_context = lambda message, **context: log_with_context("DEBUG", message, **context)
logger.info_with_context = lambda message, **context: log_with_context("INFO", message, **context)
logger.warning_with_context = lambda message, **context: log_with_context("WARNING", message, **context)
logger.error_with_context = lambda message, **context: log_with_context("ERROR", message, **context)
logger.critical_with_context = lambda message, **context: log_with_context("CRITICAL", message, **context) 