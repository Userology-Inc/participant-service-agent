import logging
from typing import Dict, Any, Optional

from livekit import rtc
# Remove the circular import
# from worker import agent
from worker.services.db import DBService
from worker.manager.rpc.interaction_handler import InteractionHandler
from worker.manager.rpc.task_handler import TaskHandler

logger = logging.getLogger("rpc-manager")

class RPCManager:
    """Manager for all RPC handlers"""
    
    def __init__(self, room: rtc.Room, agent, local_participant: rtc.LocalParticipant = None, db_service: Optional[DBService] = None):
        self.room = room
        self.agent = agent
        self.db_service = db_service or DBService()
        self.local_participant = local_participant
        
        # Initialize handlers with local participant
        self.interaction_handler = InteractionHandler(room, agent, local_participant, db_service)
        self.task_handler = TaskHandler(room, agent, local_participant, db_service)
        
        logger.info("RPC Manager initialized with LiveKit RPC support")
    
    def set_metadata(self, metadata: Dict[str, Any]):
        """Set metadata for all handlers"""
        self.interaction_handler.set_metadata(metadata)
        self.task_handler.set_metadata(metadata)
        
    def shutdown(self):
        """Shutdown the RPC manager and all handlers"""
        logger.info("Shutting down RPC Manager")
        # Any cleanup needed for handlers