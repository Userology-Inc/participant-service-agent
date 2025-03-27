import os
from typing import Dict, Any

from worker.config import Config, get_config

class DBConfig:
    """
    Configuration for the DB service.
    
    Attributes:
        url: Base URL for the DB service
        timeout: Default request timeout in seconds
    """
    def __init__(self, url: str, timeout: int = 60):
        self.url = url
        self.timeout = timeout
        
class ServiceConfig:
    """
    Global configuration container.
    
    Attributes:
        db_config: DB service configuration
    """
    def __init__(self):
        # Get global config
        worker_config = get_config()
        
        # Load database configuration
        db_url = worker_config.db_service_url or os.environ.get("DB_SERVICE_URL", "http://localhost:8080")
        db_timeout = int(os.environ.get("DB_SERVICE_TIMEOUT", "60"))
        
        self.db_config = DBConfig(url=db_url, timeout=db_timeout)
        
# Create singleton instance
config = ServiceConfig() 