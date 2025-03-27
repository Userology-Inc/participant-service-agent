import pytest
import os
import asyncio
from typing import Dict, Any

from worker.services.db import DBService, DBErrorType, DBServiceError

# Set a dummy API URL for integration testing
# This should be overridden in the test environment
API_URL = os.environ.get("TEST_DB_API_URL", "http://localhost:8080")


@pytest.fixture
def setup_test_config():
    """Set up test configuration for integration tests."""
    # Create a temporary config for testing
    original_url = None
    
    try:
        from worker.services.db.client import config
        original_url = config.db_config.url
        config.db_config.url = API_URL
        
        # Reset DBService for a fresh instance
        DBService._instance = None
        DBService._session = None
        
        yield
    finally:
        # Restore original config
        if original_url:
            config.db_config.url = original_url


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("INTEGRATION_TESTS") != "1",
    reason="Integration tests are disabled. Set INTEGRATION_TESTS=1 to enable."
)
@pytest.mark.asyncio
class TestDBServiceIntegration:
    """Integration tests for DBService.
    
    Note: These tests require a running DB API service.
    They are skipped by default and can be enabled by setting
    the INTEGRATION_TESTS environment variable to "1".
    """
    
    @pytest.fixture(autouse=True)
    def setup(self, setup_test_config):
        """Set up the test environment."""
        self.test_database_id = os.environ.get("TEST_DATABASE_ID", "test-db")
        self.test_study_id = os.environ.get("TEST_STUDY_ID", "test-study")
        
    async def test_health_check(self):
        """Test the health check endpoint."""
        result = await DBService.get_health_check()
        assert result["status"] == 200
        assert result["baseUrl"] == API_URL
        
    async def test_error_handling(self):
        """Test error handling with an invalid endpoint."""
        with pytest.raises(DBServiceError) as excinfo:
            await DBService._request("GET", "/invalid-endpoint")
        
        assert excinfo.value.error_type in (
            DBErrorType.NOT_FOUND, 
            DBErrorType.INTERNAL_SERVER_ERROR
        )


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("INTEGRATION_TESTS") != "1",
    reason="Integration tests are disabled. Set INTEGRATION_TESTS=1 to enable."
)
def test_db_service_main():
    """Run all integration tests.
    
    This function can be called directly to run the tests.
    """
    
    async def run_tests():
        # Create test instance
        test_instance = TestDBServiceIntegration()
        await test_instance.setup(None)
        
        # Run tests
        await test_instance.test_health_check()
        await test_instance.test_error_handling()
        
        print("All integration tests passed!")
        
    # Run the test coroutine
    asyncio.run(run_tests())


if __name__ == "__main__":
    # Run the tests directly if this file is executed
    test_db_service_main() 