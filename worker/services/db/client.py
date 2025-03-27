import http.client
import json
import time
import enum
from typing import Any, Dict, List, Optional, TypeVar, Union, Tuple
import urllib.parse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Local imports
from worker.services.db.types import DBErrorType, DBServiceError, ERROR_MESSAGES, ApiResponse
from worker.services.db.log import setup_logger, log_request, log_response, log_error, logger
from worker.services.db.config import config

# Initialize logger
logger = setup_logger()

# Retry configuration
RETRY_CONFIG = {
    'max_retries': 3,
    'initial_retry_delay': 1.0,  # 1 second
    'max_retry_delay': 10.0,  # 10 seconds
}

class DBService:
    """
    A client for interacting with the database service.
    
    This service handles communication with the backend database API,
    including error handling, retries, and logging.
    """
    
    _instance = None
    _session = None
    
    @classmethod
    def get_instance(cls):
        """
        Get the singleton instance of DBService.
        
        Returns:
            DBService: The singleton instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def _get_session(cls) -> requests.Session:
        """
        Get or create a requests session with retry configuration.
        
        Returns:
            requests.Session: Session object
        """
        if cls._session is None:
            retry_strategy = Retry(
                total=RETRY_CONFIG['max_retries'],
                backoff_factor=0.5,
                status_forcelist=[500, 502, 503, 504],
                allowed_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
            )
            
            adapter = HTTPAdapter(max_retries=retry_strategy)
            cls._session = requests.Session()
            cls._session.mount("http://", adapter)
            cls._session.mount("https://", adapter)
            cls._session.headers.update({
                'Content-Type': 'application/json',
            })
            
        return cls._session
    
    @staticmethod
    def _classify_error(status_code: Optional[int] = None, error_code: Optional[str] = None) -> DBErrorType:
        """
        Classify the error based on status code or error code.
        
        Args:
            status_code: HTTP status code
            error_code: Error code string
            
        Returns:
            DBErrorType: The classified error type
        """
        if status_code:
            if status_code == 401:
                return DBErrorType.AUTHENTICATION_ERROR
            elif status_code == 404:
                return DBErrorType.NOT_FOUND
            elif status_code == 429:
                return DBErrorType.RATE_LIMIT_EXCEEDED
            elif status_code == 500:
                return DBErrorType.INTERNAL_SERVER_ERROR
            elif status_code == 400:
                return DBErrorType.BAD_REQUEST
            elif status_code == 409:
                return DBErrorType.CONFLICT
            elif status_code == 403:
                return DBErrorType.FORBIDDEN
            elif status_code == 504:
                return DBErrorType.GATEWAY_TIMEOUT
            elif status_code == 405:
                return DBErrorType.METHOD_NOT_ALLOWED
            else:
                return DBErrorType.STATUS_CODE_ERROR
                
        if error_code == "ECONNABORTED":
            return DBErrorType.ECONNABORTED_ERROR
            
        return DBErrorType.NETWORK_ERROR
    
    @staticmethod
    def _get_error_message(status_code: int) -> str:
        """
        Get the error message for a status code.
        
        Args:
            status_code: HTTP status code
            
        Returns:
            str: Error message
        """
        return ERROR_MESSAGES.get(status_code, "Unknown error")
    
    @classmethod
    def _create_error(cls, 
                     status_code: Optional[int] = None, 
                     error_code: Optional[str] = None,
                     message: Optional[str] = None) -> DBServiceError:
        """
        Create an error with appropriate message.
        
        Args:
            status_code: HTTP status code
            error_code: Error code string
            message: Error message
            
        Returns:
            DBServiceError: The created error
        """
        error_type = cls._classify_error(status_code, error_code)
        error_message = cls._get_error_message(status_code or 500)
        
        if message:
            error_message = f"{error_message} - {message}"
            
        return DBServiceError(error_type, error_message)
    
    @classmethod
    async def _request(cls, 
                      method: str, 
                      endpoint: str, 
                      database_id: Optional[str] = None,
                      params: Optional[Dict] = None, 
                      data: Optional[Dict] = None) -> Dict:
        """
        Make an HTTP request to the DB service.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            database_id: Database ID for the header
            params: Query parameters
            data: Request body
            
        Returns:
            Dict: Response data
            
        Raises:
            DBServiceError: When the request fails
        """
        url = f"{config.db_config.url}{endpoint}"
        headers = {'x-databaseid': database_id} if database_id else {}
        session = cls._get_session()
        
        log_request(method, url, database_id, params, data)
        
        start_time = time.time()
        try:
            response = session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                headers=headers,
                timeout=60
            )
            
            duration = (time.time() - start_time) * 1000  # Convert to ms
            
            if 200 <= response.status_code < 300:
                response_data = response.json()
                log_response(method, url, response.status_code, response_data, duration)
                return response_data.get('data')
            else:
                error = cls._create_error(
                    status_code=response.status_code,
                    message=response.text
                )
                log_error(
                    error.error_type.value, 
                    response.status_code, 
                    method, 
                    url, 
                    str(error), 
                    duration
                )
                raise error
                
        except requests.exceptions.RequestException as e:
            duration = (time.time() - start_time) * 1000
            
            # Handle connection errors
            error_code = None
            if isinstance(e, requests.exceptions.ConnectTimeout):
                error_code = "ECONNABORTED"
                
            error = cls._create_error(
                error_code=error_code,
                message=str(e)
            )
            
            log_error(
                error.error_type.value, 
                None, 
                method, 
                url, 
                str(error), 
                duration
            )
            
            raise error
    
    @classmethod
    async def get_prompts(cls, prompt_id: str) -> Dict:
        """
        Get prompts by ID.
        
        Args:
            prompt_id: The ID of the prompt
            
        Returns:
            Dict: Prompt data
        """
        return await cls._request('GET', f'/api/prompts/{prompt_id}', database_id='main')
    
    @classmethod
    async def get_avatar(cls, avatar_id: str) -> Dict:
        """
        Get avatar by ID.
        
        Args:
            avatar_id: The ID of the avatar
            
        Returns:
            Dict: Avatar data
        """
        return await cls._request('GET', f'/api/avatar/{avatar_id}', database_id='playground')
    
    @classmethod
    async def get_study_logos(cls, database_id: str) -> List[Dict]:
        """
        Get study logos.
        
        Args:
            database_id: The database ID
            
        Returns:
            List[Dict]: List of study logos
        """
        return await cls._request('GET', '/api/preferences/logos', database_id=database_id)
    
    @classmethod
    async def get_study_data(cls, database_id: str, study_id: str) -> Dict:
        """
        Get study data by ID.
        
        Args:
            database_id: The database ID
            study_id: The study ID
            
        Returns:
            Dict: Study data
            
        Raises:
            DBServiceError: When the request fails
        """
        try:
            return await cls._request('GET', f'/api/study/{study_id}', database_id=database_id)
        except Exception as e:
            logger.error(f"Error in get_study_data: {getattr(e, 'code', None)} {str(e)}")
            raise Exception(str(e) or "Error in get_study_data")
    
    @classmethod
    async def update_study_data(cls, database_id: str, study_id: str, data: Dict) -> Dict:
        """
        Update study data.
        
        Args:
            database_id: The database ID
            study_id: The study ID
            data: Data to update
            
        Returns:
            Dict: Updated study data
        """
        return await cls._request('PATCH', f'/api/study/{study_id}', database_id=database_id, data=data)
    
    @classmethod
    async def get_guides(cls, 
                       database_id: str, 
                       study_id: str, 
                       task_id: Optional[str] = None, 
                       version: Optional[str] = None) -> List[Dict]:
        """
        Get study guides.
        
        Args:
            database_id: The database ID
            study_id: The study ID
            task_id: Optional task ID filter
            version: Optional version filter
            
        Returns:
            List[Dict]: List of guides
        """
        params = {}
        if task_id:
            params['taskId'] = task_id
        if version:
            params['version'] = version
            
        return await cls._request(
            'GET', 
            f'/api/study/{study_id}/guides', 
            database_id=database_id,
            params=params
        )
    
    @classmethod
    async def get_participant_data(cls, database_id: str, study_id: str, participant_id: str) -> Dict:
        """
        Get participant data.
        
        Args:
            database_id: The database ID
            study_id: The study ID
            participant_id: The participant ID
            
        Returns:
            Dict: Participant data
        """
        return await cls._request(
            'GET',
            f'/api/study/{study_id}/participants/{participant_id}',
            database_id=database_id
        )
    
    @classmethod
    async def upsert_participant_data(cls, 
                                    database_id: str, 
                                    study_id: str, 
                                    participant_id: str, 
                                    data: Dict) -> Dict:
        """
        Update or insert participant data.
        
        Args:
            database_id: The database ID
            study_id: The study ID
            participant_id: The participant ID
            data: Data to update
            
        Returns:
            Dict: Updated participant data
        """
        return await cls._request(
            'PATCH',
            f'/api/study/{study_id}/participants/{participant_id}',
            database_id=database_id,
            data=data
        )
    
    @classmethod
    async def get_session_data(cls, 
                             database_id: str, 
                             study_id: str, 
                             participant_id: str, 
                             session_id: str) -> Dict:
        """
        Get session data.
        
        Args:
            database_id: The database ID
            study_id: The study ID
            participant_id: The participant ID
            session_id: The session ID
            
        Returns:
            Dict: Session data
            
        Raises:
            Exception: When the request fails
        """
        try:
            return await cls._request(
                'GET',
                f'/api/study/{study_id}/participants/{participant_id}/sessions/{session_id}',
                database_id=database_id
            )
        except Exception as e:
            logger.error(f"Error in get_session_data: {getattr(e, 'code', None)} {str(e)}")
            raise Exception(str(e) or "Error in get_session_data")
    
    @classmethod
    async def update_session_data(cls, 
                                database_id: str, 
                                study_id: str, 
                                participant_id: str, 
                                session_id: str,
                                data: Dict) -> Dict:
        """
        Update session data.
        
        Args:
            database_id: The database ID
            study_id: The study ID
            participant_id: The participant ID
            session_id: The session ID
            data: Data to update
            
        Returns:
            Dict: Updated session data
        """
        return await cls._request(
            'PATCH',
            f'/api/study/{study_id}/participants/{participant_id}/sessions/{session_id}',
            database_id=database_id,
            data=data
        )
    
    @classmethod
    async def get_latest_guides(cls, database_id: str, study_id: str, as_array: bool = False) -> Union[List[Dict], Dict]:
        """
        Get latest guides.
        
        Args:
            database_id: The database ID
            study_id: The study ID
            as_array: Whether to return as array
            
        Returns:
            Union[List[Dict], Dict]: Latest guides
        """
        return await cls._request(
            'GET',
            f'/api/study/{study_id}/latestGuides',
            database_id=database_id,
            params={'asArray': str(as_array).lower()}
        )
    
    @classmethod
    async def get_latest_session_id(cls, database_id: str) -> str:
        """
        Get latest session ID.
        
        Args:
            database_id: The database ID
            
        Returns:
            str: Latest session ID
        """
        return await cls._request(
            'GET',
            '/api/study/latestSession',
            database_id=database_id
        )
    
    @classmethod
    async def get_file_key_data(cls, database_id: str, file_key: str) -> Dict:
        """
        Get Figma file key data.
        
        Args:
            database_id: The database ID
            file_key: The Figma file key
            
        Returns:
            Dict: File key data
        """
        return await cls._request(
            'GET',
            '/api/figma/collection',
            database_id=database_id,
            params={'fileKey': file_key}
        )
    
    @classmethod
    async def load_file_key(cls, database_id: str, file_key: str) -> Dict:
        """
        Load Figma file key.
        
        Args:
            database_id: The database ID
            file_key: The Figma file key
            
        Returns:
            Dict: Loaded file key data
        """
        return await cls._request(
            'GET',
            '/api/figma/collection/load',
            database_id=database_id,
            params={'fileKey': file_key}
        )
    
    @classmethod
    async def get_figma_frame_data(cls, database_id: str, file_key: str, frame_id: str) -> Dict:
        """
        Get Figma frame data.
        
        Args:
            database_id: The database ID
            file_key: The Figma file key
            frame_id: The frame ID
            
        Returns:
            Dict: Frame data
        """
        return await cls._request(
            'GET',
            '/api/figma/collection',
            database_id=database_id,
            params={'fileKey': file_key, 'frameId': frame_id}
        )
    
    @classmethod
    async def get_frame_description(cls, database_id: str, file_key: str, frame_id: str) -> str:
        """
        Get frame description.
        
        Args:
            database_id: The database ID
            file_key: The Figma file key
            frame_id: The frame ID
            
        Returns:
            str: Frame description
        """
        figma_data = await cls.get_figma_frame_data(database_id, file_key, frame_id)
        return figma_data.get('imageDescription')
    
    @classmethod
    async def get_frame_public_url(cls, database_id: str, file_key: str, frame_id: str) -> str:
        """
        Get frame public URL.
        
        Args:
            database_id: The database ID
            file_key: The Figma file key
            frame_id: The frame ID
            
        Returns:
            str: Frame public URL
        """
        figma_data = await cls.get_figma_frame_data(database_id, file_key, frame_id)
        return figma_data.get('imageLink')
    
    @classmethod
    async def get_frame_name(cls, database_id: str, file_key: str, frame_id: str) -> str:
        """
        Get frame name.
        
        Args:
            database_id: The database ID
            file_key: The Figma file key
            frame_id: The frame ID
            
        Returns:
            str: Frame name
        """
        figma_data = await cls.get_figma_frame_data(database_id, file_key, frame_id)
        return figma_data.get('frameName')
    
    @classmethod
    async def get_component_description(cls, 
                                      database_id: str, 
                                      file_key: str, 
                                      frame_id: str, 
                                      node_id: str) -> str:
        """
        Get component description.
        
        Args:
            database_id: The database ID
            file_key: The Figma file key
            frame_id: The frame ID
            node_id: The node ID
            
        Returns:
            str: Component description
        """
        figma_data = await cls.get_figma_frame_data(database_id, file_key, frame_id)
        parent_node_id = figma_data.get('bestParents', {}).get(node_id)
        node_to_use = parent_node_id or node_id
        return figma_data.get('nodes', {}).get(node_to_use, {}).get('description')
    
    @classmethod
    async def get_config(cls, database_id: str, config_id: str) -> Optional[Dict]:
        """
        Get configuration.
        
        Args:
            database_id: The database ID
            config_id: The configuration ID
            
        Returns:
            Optional[Dict]: Configuration or None if not found
        """
        try:
            return await cls._request(
                'GET',
                f'/api/config/{config_id}',
                database_id=database_id
            )
        except Exception:
            return None
    
    @classmethod
    async def get_preference_doc(cls, database_id: str, doc_id: str) -> Dict:
        """
        Get preference document.
        
        Args:
            database_id: The database ID
            doc_id: The document ID
            
        Returns:
            Dict: Preference document
        """
        return await cls._request(
            'GET',
            f'/api/preferences/{doc_id}',
            database_id=database_id
        )
    
    @classmethod
    async def update_preference_doc(cls, database_id: str, doc_id: str, data: Dict) -> bool:
        """
        Update preference document.
        
        Args:
            database_id: The database ID
            doc_id: The document ID
            data: Data to update
            
        Returns:
            bool: Success status
        """
        result = await cls._request(
            'PATCH',
            f'/api/preferences/{doc_id}',
            database_id=database_id,
            data=data
        )
        return result.get('success', False)
    
    @classmethod
    async def get_health_check(cls) -> Dict:
        """
        Get health check status.
        
        Returns:
            Dict: Health check status
        """
        response = await cls._request('GET', '/api/healthCheck')
        return {
            'status': 200,  # We assume 200 since request succeeded
            'baseUrl': config.db_config.url
        }
