import unittest
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import json
import requests
import time

from worker.services.db import DBService, DBErrorType, DBServiceError


class TestDBServiceBase(unittest.TestCase):
    """Base test class for DBService with common setup and teardown."""

    def setUp(self):
        """Set up test fixtures"""
        # Reset the singleton instances before each test
        DBService._instance = None
        DBService._session = None
        
        # Create mock config
        mock_db_config = MagicMock()
        mock_db_config.url = 'https://api.example.com'
        mock_db_config.timeout = 60
        
        self.mock_config = MagicMock()
        self.mock_config.db_config = mock_db_config
        
        # Create patcher for config
        self.config_patcher = patch('worker.services.db.client.config', self.mock_config)
        self.config_patcher.start()
        
    def tearDown(self):
        """Tear down test fixtures"""
        self.config_patcher.stop()


class TestDBServiceUtils(TestDBServiceBase):
    """Tests for DBService utility methods."""
    
    @patch('worker.services.db.client.requests.Session')
    def test_get_session(self, mock_session):
        """Test session creation with proper configuration"""
        # Setup
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        
        # Execute
        session = DBService._get_session()
        
        # Assert
        self.assertEqual(session, mock_session_instance)
        mock_session_instance.mount.assert_any_call("http://", unittest.mock.ANY)
        mock_session_instance.mount.assert_any_call("https://", unittest.mock.ANY)
        mock_session_instance.headers.update.assert_called_once()
        
    def test_classify_error(self):
        """Test error classification based on status codes"""
        # Test status code classifications
        self.assertEqual(DBService._classify_error(401), DBErrorType.AUTHENTICATION_ERROR)
        self.assertEqual(DBService._classify_error(404), DBErrorType.NOT_FOUND)
        self.assertEqual(DBService._classify_error(429), DBErrorType.RATE_LIMIT_EXCEEDED)
        self.assertEqual(DBService._classify_error(500), DBErrorType.INTERNAL_SERVER_ERROR)
        self.assertEqual(DBService._classify_error(400), DBErrorType.BAD_REQUEST)
        self.assertEqual(DBService._classify_error(409), DBErrorType.CONFLICT)
        self.assertEqual(DBService._classify_error(403), DBErrorType.FORBIDDEN)
        self.assertEqual(DBService._classify_error(504), DBErrorType.GATEWAY_TIMEOUT)
        self.assertEqual(DBService._classify_error(405), DBErrorType.METHOD_NOT_ALLOWED)
        self.assertEqual(DBService._classify_error(499), DBErrorType.STATUS_CODE_ERROR)
        
        # Test error code classification
        self.assertEqual(DBService._classify_error(error_code="ECONNABORTED"), 
                         DBErrorType.ECONNABORTED_ERROR)
        
        # Test default network error
        self.assertEqual(DBService._classify_error(), DBErrorType.NETWORK_ERROR)
        
    def test_get_error_message(self):
        """Test error message retrieval based on status codes"""
        self.assertEqual(DBService._get_error_message(404), "Resource not found")
        self.assertEqual(DBService._get_error_message(401), "Authentication failed")
        self.assertEqual(DBService._get_error_message(999), "Unknown error")
        
    def test_create_error(self):
        """Test error creation with appropriate types and messages"""
        # Test with status code
        error = DBService._create_error(status_code=404, message="Custom message")
        self.assertIsInstance(error, DBServiceError)
        self.assertEqual(error.error_type, DBErrorType.NOT_FOUND)
        self.assertTrue("Resource not found" in str(error))
        self.assertTrue("Custom message" in str(error))
        
        # Test with error code
        error = DBService._create_error(error_code="ECONNABORTED", message="Timeout")
        self.assertIsInstance(error, DBServiceError)
        self.assertEqual(error.error_type, DBErrorType.ECONNABORTED_ERROR)


@pytest.mark.asyncio
class TestDBServiceRequests:
    """Tests for DBService request methods."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures"""
        # Reset the singleton instances before each test
        DBService._instance = None
        DBService._session = None
        
        # Create mock config
        mock_db_config = MagicMock()
        mock_db_config.url = 'https://api.example.com'
        mock_db_config.timeout = 60
        
        self.mock_config = MagicMock()
        self.mock_config.db_config = mock_db_config
        
        # Create patcher for config
        self.config_patcher = patch('worker.services.db.client.config', self.mock_config)
        self.config_mock = self.config_patcher.start()
        
        # Create session mock
        self.mock_session = MagicMock()
        self.session_patcher = patch.object(DBService, '_get_session', return_value=self.mock_session)
        self.session_patcher.start()
        
        # Mock logging functions
        self.log_request_patcher = patch('worker.services.db.client.log_request')
        self.log_response_patcher = patch('worker.services.db.client.log_response')
        self.log_error_patcher = patch('worker.services.db.client.log_error')
        
        self.mock_log_request = self.log_request_patcher.start()
        self.mock_log_response = self.log_response_patcher.start()
        self.mock_log_error = self.log_error_patcher.start()
        
        yield
        
        # Clean up
        self.config_patcher.stop()
        self.session_patcher.stop()
        self.log_request_patcher.stop()
        self.log_response_patcher.stop()
        self.log_error_patcher.stop()
    
    async def test_request_success(self):
        """Test successful request handling"""
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"key": "value"}}
        
        self.mock_session.request.return_value = mock_response
        
        # Execute
        result = await DBService._request("GET", "/test", "test-db", {"param": "value"}, {"body": "data"})
        
        # Assert
        self.mock_session.request.assert_called_once_with(
            method="GET",
            url="https://api.example.com/test",
            params={"param": "value"},
            json={"body": "data"},
            headers={"x-databaseid": "test-db"},
            timeout=60
        )
        self.mock_log_request.assert_called_once()
        self.mock_log_response.assert_called_once()
        assert result == {"key": "value"}
    
    async def test_request_http_error(self):
        """Test HTTP error handling"""
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        
        self.mock_session.request.return_value = mock_response
        
        # Execute and assert
        with pytest.raises(DBServiceError) as excinfo:
            await DBService._request("GET", "/test", "test-db")
            
        assert excinfo.value.error_type == DBErrorType.NOT_FOUND
        self.mock_log_request.assert_called_once()
        self.mock_log_error.assert_called_once()
    
    async def test_request_network_error(self):
        """Test network error handling"""
        # Setup
        self.mock_session.request.side_effect = requests.exceptions.ConnectionError("Connection refused")
        
        # Execute and assert
        with pytest.raises(DBServiceError) as excinfo:
            await DBService._request("GET", "/test", "test-db")
            
        assert excinfo.value.error_type == DBErrorType.NETWORK_ERROR
        self.mock_log_request.assert_called_once()
        self.mock_log_error.assert_called_once()
    
    @patch.object(DBService, '_request', new_callable=AsyncMock)
    async def test_get_prompts(self, mock_request):
        """Test get_prompts method"""
        # Setup
        mock_request.return_value = {"prompt": "test prompt"}
        
        # Execute
        result = await DBService.get_prompts("123")
        
        # Assert
        mock_request.assert_called_once_with(
            'GET', '/api/prompts/123', database_id='main'
        )
        assert result == {"prompt": "test prompt"}
    
    @patch.object(DBService, '_request', new_callable=AsyncMock)
    async def test_get_study_data(self, mock_request):
        """Test get_study_data method"""
        # Setup
        mock_request.return_value = {"study": "study data"}
        
        # Execute
        result = await DBService.get_study_data("db-123", "study-456")
        
        # Assert
        mock_request.assert_called_once_with(
            'GET', '/api/study/study-456', database_id='db-123'
        )
        assert result == {"study": "study data"}
    
    @patch.object(DBService, '_request', new_callable=AsyncMock)
    async def test_get_study_data_error(self, mock_request):
        """Test get_study_data method error handling"""
        # Setup
        mock_request.side_effect = Exception("API error")
        
        # Execute and assert
        with pytest.raises(Exception) as excinfo:
            await DBService.get_study_data("db-123", "study-456")
            
        assert str(excinfo.value) == "API error"
    
    @patch.object(DBService, '_request', new_callable=AsyncMock)
    async def test_update_session_data(self, mock_request):
        """Test update_session_data method"""
        # Setup
        mock_request.return_value = {"session": "updated"}
        session_data = {"status": "completed"}
        
        # Execute
        result = await DBService.update_session_data(
            "db-123", "study-456", "participant-789", "session-abc", session_data
        )
        
        # Assert
        mock_request.assert_called_once_with(
            'PATCH', 
            '/api/study/study-456/participants/participant-789/sessions/session-abc',
            database_id='db-123', 
            data=session_data
        )
        assert result == {"session": "updated"}
        
    @patch.object(DBService, '_request', new_callable=AsyncMock)
    async def test_get_health_check(self, mock_request):
        """Test get_health_check method"""
        # Setup
        mock_request.return_value = {"status": "ok"}
        
        # Execute
        result = await DBService.get_health_check()
        
        # Assert
        mock_request.assert_called_once_with('GET', '/api/healthCheck')
        assert result["status"] == 200
        assert result["baseUrl"] == self.mock_config.db_config.url 