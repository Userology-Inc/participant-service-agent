import json
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

from livekit import rtc
from livekit.agents import llm, TimedTranscript, Word
from livekit.agents.pipeline.pipeline_agent import VoicePipelineAgent

from worker.services.db import DBService
from worker.types.message import ExternalMessageType
from worker.types.rpc import (
    RPCMethod, 
    RPCResponse, 
    ComponentClickPayload, 
    ScreenChangePayload, 
    TranscribedTextPayload
)

logger = logging.getLogger("interaction-handler")

class InteractionHandler:
    """Handler for interaction RPC messages"""
    
    def __init__(self, room: rtc.Room, agent: VoicePipelineAgent, local_participant: rtc.LocalParticipant = None, db_service: Optional[DBService] = None):
        self.room = room
        self.agent = agent
        self.db_service = db_service or DBService()
        self.metadata = {}
        self.local_participant = local_participant
        
        # Register RPC methods if local participant is available
        if self.local_participant:
            self._register_rpc_methods()
        else:
            # Fallback to event listener if local participant is not provided
            logger.warning("Local participant not provided, will try to register methods when participant connects")
            room.on("participant_connected", self._on_participant_connected)
        
        logger.info("Interaction handler initialized")
        
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
            RPCMethod.HANDLE_COMPONENT_CLICK: self._handle_component_click_rpc,
            RPCMethod.HANDLE_SCREEN_CHANGE: self._handle_screen_change_rpc,
            RPCMethod.HANDLE_TRANSCRIBED_TEXT: self._handle_transcribed_text_rpc
        }
        
        for method, handler in rpc_methods.items():
            self.local_participant.register_rpc_method(method, handler)
        
        logger.info("Registered interaction RPC methods")
    
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
    
    async def _handle_component_click_rpc(self, data: rtc.RpcInvocationData) -> str:
        """Handle component click RPC invocation"""
        try:
            logger.info(f"Received component click RPC: {data}")
            payload = await self._parse_rpc_payload(data)
            
            # Extract fields with safe defaults
            tenant_id = payload.get("tenantId")
            file_key = payload.get("fileKey")
            frame_id = payload.get("frameId")
            node_id = payload.get("nodeId")
            new_frame_id = payload.get("newFrameId")
            timestamp = payload.get("timestamp")
            animation = payload.get("animation", False)
            
            # Validate required fields
            required_fields = {"tenantId": tenant_id, "fileKey": file_key, "frameId": frame_id}
            missing_fields = [k for k, v in required_fields.items() if not v]
            
            if missing_fields:
                error_msg = f"Missing required fields: {', '.join(missing_fields)}"
                logger.error(error_msg)
                return self._create_response(False, error_msg)
            
            # Get component and frame information
            node_description = await asyncio.to_thread(
                self.db_service.get_component_description,
                tenant_id, file_key, frame_id, node_id
            )
            
            frame_name = await asyncio.to_thread(
                self.db_service.get_frame_name,
                tenant_id, file_key, frame_id
            )
            
            new_frame_name = "Some Frame"
            if new_frame_id:
                new_frame_name = await asyncio.to_thread(
                    self.db_service.get_frame_name,
                    tenant_id, file_key, new_frame_id
                )
            
            # Create interaction message
            interaction_message = self._create_interaction_message(
                frame_name, new_frame_id, frame_id, node_description, 
                new_frame_name, animation
            )
            
            # Add to chat context
            if interaction_message:
                await self._add_to_chat_context(interaction_message, ExternalMessageType.INTERACTION, timestamp)
            else:
                logger.warn("Interaction message is empty")
            
            # If there's a new frame, handle screen change
            if new_frame_id and new_frame_id != frame_id:
                screen_change_data = {**payload, "frameId": new_frame_id}
                await self._handle_screen_change(screen_change_data)
            
            return self._create_response(True)
                
        except Exception as e:
            logger.error(f"Error handling component click RPC: {str(e)}")
            return self._create_response(False, str(e))
    
    def _create_interaction_message(self, frame_name, new_frame_id, frame_id, 
                                   node_description, new_frame_name, animation):
        """Create appropriate interaction message based on context"""
        if not frame_name:
            return ""
            
        if new_frame_id == frame_id:
            return f"[[Clicked on '{node_description or 'somewhere'}' on '{frame_name}' screen]]"
        elif animation:
            return f"[[Animation on '{frame_name}' screen moved user to '{new_frame_name}' screen]]"
        elif new_frame_id:
            return f"[[Clicked on '{node_description or 'somewhere'}' on '{frame_name}' screen and moved to '{new_frame_name}' screen]]"
        else:
            return f"[[Misclicked on '{node_description or 'somewhere'}' on '{frame_name}' screen and didn't open any screen]]"
    
    async def _handle_screen_change_rpc(self, data: rtc.RpcInvocationData) -> str:
        """Handle screen change RPC invocation"""
        try:
            payload = await self._parse_rpc_payload(data)
            await self._handle_screen_change(payload)
            return self._create_response(True)
            
        except Exception as e:
            logger.error(f"Error handling screen change RPC: {str(e)}")
            return self._create_response(False, str(e))
    
    async def _handle_transcribed_text_rpc(self, data: rtc.RpcInvocationData) -> str:
        """Handle transcribed text RPC invocation"""
        try:
            payload = await self._parse_rpc_payload(data)
            
            transcribed_text = payload.get("transcribedText")
            timestamp = payload.get("timestamp")
            
            if not transcribed_text or not timestamp:
                return self._create_response(
                    False, 
                    "Invalid data", 
                    {"transcribedText": transcribed_text, "timestamp": timestamp}
                )
            
            # Format and add to chat context
            formatted_text = f"[[{transcribed_text}]]"
            await self._add_to_chat_context(formatted_text, ExternalMessageType.INTERACTION, timestamp)
            
            return self._create_response(True)
            
        except Exception as e:
            logger.error(f"Error handling transcribed text RPC: {str(e)}")
            return self._create_response(False, str(e))
    
    async def _handle_screen_change(self, data: Dict[str, Any]):
        """Handle screen change events"""
        try:
            tenant_id = data.get("tenantId")
            file_key = data.get("fileKey")
            frame_id = data.get("frameId")
            timestamp = data.get("timestamp")
            
            # Get frame information
            frame_name = await asyncio.to_thread(
                self.db_service.get_frame_name,
                tenant_id, file_key, frame_id
            )
            
            frame_description = await asyncio.to_thread(
                self.db_service.get_frame_description,
                tenant_id, file_key, frame_id
            )
            
            # Create system message with frame description
            if frame_description and frame_name:
                system_message = f"### Description of {frame_name}: {frame_description} ###"
               
                await self._update_interaction_system_message(system_message)
            
        except Exception as e:
            logger.error(f"Error handling screen change: {str(e)}")
    
    async def _add_to_chat_context(self, content: str, message_type: ExternalMessageType, timestamp: int):
        """Add interaction message to chat context"""
        try:
            # Create a timed transcript for the interaction
            timed_transcript = TimedTranscript(
                type="transcript",
                role="user",
                content=content,
                start=timestamp, 
                end=timestamp,
                words=[]
            )
            
            chat_message = llm.ChatMessage(role="user", content=content)
            self.agent.chat_ctx.append(chat_message);
        

            
            logger.info(f"Added interaction to chat context: {content}")

            # # Trigger any necessary callbacks
            if hasattr(self.agent, "on_user_speech_committed"):
                logger.info(f"Triggering on_user_speech_committed callback")
                self.agent.on_user_speech_committed(chat_message, timed_transcript)
                
        except Exception as e:
            logger.error(f"Error adding to chat context: {str(e)}")
    async def _update_interaction_system_message(self, content: str):
        """Update the interaction system message"""
        self.agent.chat_ctx.update_message(1, llm.ChatMessage(role="system", content=content));
        
    def set_metadata(self, metadata: Dict[str, Any]):
        """Set metadata for the interaction handler"""
        self.metadata = metadata
    