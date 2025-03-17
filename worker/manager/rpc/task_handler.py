import json
import logging
import asyncio
from typing import Dict, Any, Optional, List

from livekit import rtc
from livekit.agents import llm, TimedTranscript

from worker.services.db import DBService
from worker.types.message import ExternalMessageType
from worker.types.rpc import (
    RPCMethod,
    RPCResponse,
    TaskStartPayload,
    TaskEndPayload,
    TaskSkipPayload
)

logger = logging.getLogger("task-handler")

class TaskHandler:
    """Handler for task-related RPC messages"""
    
    def __init__(self, room: rtc.Room, agent, local_participant: rtc.LocalParticipant = None, db_service: Optional[DBService] = None):
        self.room = room
        self.agent = agent
        self.db_service = db_service or DBService()
        self.metadata = {}
        self.current_task = None
        self.local_participant = local_participant
        
        # Register RPC methods if local participant is available
        if self.local_participant:
            self._register_rpc_methods()
        else:
            # Fallback to event listener if local participant is not provided
            logger.warning("Local participant not provided, will try to register methods when participant connects")
            room.on("participant_connected", self._on_participant_connected)
        
        logger.info("Task handler initialized")
        
    def _on_participant_connected(self, participant: rtc.LocalParticipant):
        """Handle participant connected event"""
        if isinstance(participant, rtc.LocalParticipant):
            self.local_participant = participant
            self._register_rpc_methods()
    
    def _register_rpc_methods(self):
        """Register RPC methods for the local participant"""
        if not self.local_participant:
            logger.warning("Cannot register RPC methods: No local participant available")
            return
            
        rpc_methods = {
            RPCMethod.HANDLE_TASK_START: self._handle_task_start_rpc,
            RPCMethod.HANDLE_TASK_END: self._handle_task_end_rpc,
            RPCMethod.HANDLE_TASK_SKIP: self._handle_task_skip_rpc
        }
        
        for method, handler in rpc_methods.items():
            self.local_participant.register_rpc_method(method, handler)
        
        logger.info("Registered task RPC methods")
    
    async def _parse_rpc_payload(self, data: rtc.RpcInvocationData) -> Dict[str, Any]:
        """Parse RPC payload with error handling"""
        try:
            payload_str = data.payload
            if not payload_str or not payload_str.strip():
                raise ValueError("Empty payload received")
            
            return json.loads(payload_str)
        except json.JSONDecodeError as json_err:
            logger.error(f"JSON parsing error: {str(json_err)}, payload: {data.payload[:100]}...")
            raise ValueError(f"Invalid JSON payload: {str(json_err)}")
    
    def _create_response(self, success: bool, message: str = None, data: Dict = None) -> str:
        """Create a standardized JSON response"""
        response = {"success": success}
        if message:
            response["message"] = message
        if data:
            response["data"] = data
        return json.dumps(response)
    
    async def _handle_task_start_rpc(self, data: rtc.RpcInvocationData) -> str:
        """Handle task start RPC invocation"""
        try:
            logger.info(f"Received task start RPC: {data}")
            payload = await self._parse_rpc_payload(data)
            
            task_number = payload.get("taskNumber")
            task_name = payload.get("taskName")
            task_description = payload.get("taskDescription")
            task_instructions = payload.get("taskInstructions")
            timestamp = payload.get("timestamp")
            
            # Validate required fields
            required_fields = {"taskNumber": task_number, "taskName": task_name}
            missing_fields = [k for k, v in required_fields.items() if not v]
            
            if missing_fields:
                error_msg = f"Missing required fields: {', '.join(missing_fields)}"
                logger.error(error_msg)
                return self._create_response(False, error_msg)
            
            # Store current task
            self.current_task = {
                "number": task_number,
                "name": task_name,
                "description": task_description,
                "instructions": task_instructions
            }
            
            # Create task start message
            # task_message = f"### Starting Task {task_number}: {task_name} ###\n{task_description}\n{task_instructions}"
            task_message=f"~~ Section ${task_number + 1} starts~~"
            
            # Add as external message
            await self._add_to_chat_context(
                task_message, 
                ExternalMessageType.SECTION_START, 
                timestamp
            )
            
            return self._create_response(True)
            
        except Exception as e:
            logger.error(f"Error handling task start RPC: {str(e)}")
            return self._create_response(False, str(e))
    
    async def _handle_task_end_rpc(self, data: rtc.RpcInvocationData) -> str:
        """Handle task end RPC invocation"""
        try:
            logger.info(f"Received task end RPC: {data}")
            payload = await self._parse_rpc_payload(data)
            
            task_number = payload.get("taskNumber")
            timestamp = payload.get("timestamp")
            
            # Validate required fields
            if not task_number:
                error_msg = "Missing required field: taskNumber"
                logger.error(error_msg)
                return self._create_response(False, error_msg)
            
            task_message=f"~~ Section ${task_number + 1} completed~~"
            
            # Add as external message
            await self._add_to_chat_context(
                task_message, 
                ExternalMessageType.SECTION_END, 
                timestamp
            )
            
            # Reset current task
            self.current_task = None
            
            return self._create_response(True)
            
        except Exception as e:
            logger.error(f"Error handling task end RPC: {str(e)}")
            return self._create_response(False, str(e))
    
    async def _handle_task_skip_rpc(self, data: rtc.RpcInvocationData) -> str:
        """Handle task skip RPC invocation"""
        try:
            logger.info(f"Received task skip RPC: {data}")
            payload = await self._parse_rpc_payload(data)
            
            task_number = payload.get("taskNumber")
            timestamp = payload.get("timestamp")
            
            # Validate required fields
            if not task_number:
                error_msg = "Missing required field: taskNumber"
                logger.error(error_msg)
                return self._create_response(False, error_msg)
            
            # Create task skip message
            # task_message = f"### Skipped Task {task_number} ###"
            task_message=f"~~ Section ${task_number + 1} skipped~~"
            # Add as external message
            await self._add_to_chat_context(
                task_message, 
                ExternalMessageType.SECTION_SKIP, 
                timestamp
            )
            
            # Reset current task
            self.current_task = None
            
            return self._create_response(True)
            
        except Exception as e:
            logger.error(f"Error handling task skip RPC: {str(e)}")
            return self._create_response(False, str(e))
    
    async def _add_to_chat_context(self, content: str, message_type: ExternalMessageType, timestamp: int):
        """Add task message to chat context"""
        try:
            # Create a timed transcript for the task event
            timed_transcript = TimedTranscript(
                type="transcript",
                role="user",
                content=content,
                start=timestamp,
                end=timestamp,
                words=[]
            )
            
            # Create chat message
            chat_message = llm.ChatMessage(role="user", content=content)
            self.agent.chat_ctx.append(chat_message)
            
            logger.info(f"Added task event to chat context: {content}")
            
            # Trigger any necessary callbacks
            if hasattr(self.agent, "on_user_speech_committed"):
                logger.info(f"Triggering on_user_speech_committed callback")
                self.agent.on_user_speech_committed(chat_message, timed_transcript)
                
        except Exception as e:
            logger.error(f"Error adding to chat context: {str(e)}")
    
    
    def set_metadata(self, metadata: Dict[str, Any]):
        """Set metadata for the task handler"""
        self.metadata = metadata 