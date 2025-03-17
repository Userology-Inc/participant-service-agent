import os
import requests
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger("db-service")

class DBService:
    """Service to interact with the database API"""
    _instance = None
    def __init__(self, base_url=None):
        self.base_url = base_url or os.getenv("DB_SERVICE_URL", "https://prod.userology.info/db")
    
    @staticmethod
    def get_instance(base_url=None):
        """Get singleton instance of DBService"""
        if DBService._instance is None:
            DBService._instance = DBService(base_url)
        return DBService._instance
        
    def _make_request(self, method: str, endpoint: str, headers: Dict = None, params: Dict = None, data: Dict = None) -> Dict:
        """Make a request to the DB service API"""
        url = f"{self.base_url}{endpoint}"
        default_headers = {"Content-Type": "application/json"}
        
        if headers:
            default_headers.update(headers)
            
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=default_headers,
                params=params,
                json=data
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making request to {url}: {str(e)}")
            raise
    
    def get_study_data(self, tenant_id: str, study_id: str) -> Dict:
        """Get study data from the database"""
        headers = {"x-databaseid": tenant_id}
        return self._make_request("GET", f"/api/study/{study_id}", headers=headers)["data"]
    
    def get_participant_data(self, tenant_id: str, study_id: str, participant_id: str) -> Dict:
        """Get participant data from the database"""
        headers = {"x-databaseid": tenant_id}
        return self._make_request("GET", f"/api/study/{study_id}/participants/{participant_id}", headers=headers)["data"]
    
    def get_session_data(self, tenant_id: str, study_id: str, participant_id: str, session_id: str) -> Dict:
        """Get session data from the database"""
        headers = {"x-databaseid": tenant_id}
        return self._make_request(
            "GET", 
            f"/api/study/{study_id}/participants/{participant_id}/sessions/{session_id}", 
            headers=headers
        )["data"]
    
    def update_session_data(self, tenant_id: str, study_id: str, participant_id: str, session_id: str, data: Dict) -> Dict:
        """Update session data in the database"""
        headers = {"x-databaseid": tenant_id}
        return self._make_request(
            "PATCH", 
            f"/api/study/{study_id}/participants/{participant_id}/sessions/{session_id}", 
            headers=headers,
            data=data
        )["data"]
    
    def get_frame_name(self, tenant_id: str, file_key: str, frame_id: str) -> str:
        """Get frame name from the database"""
        headers = {"x-databaseid": tenant_id}
        params = {"fileKey": file_key, "frameId": frame_id}
        response = self._make_request("GET", "/api/figma/collection", headers=headers, params=params)
        return response["data"]["frameName"]
    
    def get_frame_description(self, tenant_id: str, file_key: str, frame_id: str) -> str:
        """Get frame description from the database"""
        headers = {"x-databaseid": tenant_id}
        params = {"fileKey": file_key, "frameId": frame_id}
        response = self._make_request("GET", "/api/figma/collection", headers=headers, params=params)
        return response["data"]["imageDescription"]
    
    def get_component_description(self, tenant_id: str, file_key: str, frame_id: str, node_id: str) -> str:
        """Get component description from the database"""
        headers = {"x-databaseid": tenant_id}
        params = {"fileKey": file_key, "frameId": frame_id}
        response = self._make_request("GET", "/api/figma/collection", headers=headers, params=params)
        figma_data = response["data"]
        parent_node_id = figma_data.get("bestParents", {}).get(node_id)
        return figma_data.get("nodes", {}).get(parent_node_id or node_id, {}).get("description") 