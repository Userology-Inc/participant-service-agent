import logging
import json
import time
from typing import Dict, Optional, Any, Union

# Set up logger
logger = logging.getLogger("db_service")

def setup_logger(log_level: str = "INFO"):
    """
    Set up the DB service logger with the specified log level.
    
    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Get log level from string
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure logger
    logger.setLevel(level)
    
    # Create console handler if not already set up
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger

def log_request(
    method: str, 
    url: str, 
    database_id: Optional[str] = None, 
    params: Optional[Dict] = None, 
    data: Optional[Dict] = None
):
    """
    Log API request details securely.
    
    Args:
        method: HTTP method
        url: Request URL
        database_id: Database ID
        params: Request parameters
        data: Request body
    """
    logger.info(
        f"[DB_SERVICE] Req: method={method.upper()}, url={url}, "
        f"databaseId={database_id or 'none'}, "
        f"requestParams={json.dumps(params) if params else 'none'}, "
        f"requestBody={'present' if data else 'none'}"
    )

def log_response(
    method: str, 
    url: str, 
    status_code: int, 
    data: Any, 
    duration: float
):
    """
    Log API response details.
    
    Args:
        method: HTTP method
        url: Request URL
        status_code: Response status code
        data: Response data
        duration: Request duration in milliseconds
    """
    try:
        data_size = len(json.dumps(data)) if data else 0
    except (TypeError, OverflowError):
        data_size = "unknown"
        
    logger.info(
        f"[DB_SERVICE] Res: method={method.upper()}, url={url}, "
        f"status={status_code}, "
        f"dataSize={data_size} bytes, "
        f"duration={duration:.2f}ms"
    )

def log_error(
    error_type: str,
    status_code: Optional[int], 
    method: str, 
    url: str, 
    message: str, 
    duration: float
):
    """
    Log API errors.
    
    Args:
        error_type: Type of error
        status_code: HTTP status code
        method: HTTP method
        url: Request URL
        message: Error message
        duration: Request duration in milliseconds
    """
    logger.error(
        f"[DB_SERVICE] Err: errorType={error_type}, "
        f"status={status_code or 'none'}, "
        f"method={method.upper()}, url={url}, "
        f"message={message}, duration={duration:.2f}ms"
    )

# Initialize logger with default settings
setup_logger()
