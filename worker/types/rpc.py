from typing import Dict, Any, TypedDict, Optional
from enum import Enum

class RPCMethod(str, Enum):
    """RPC methods that can be registered"""
    # Interaction methods
    HANDLE_COMPONENT_CLICK = "componentClick"
    HANDLE_SCREEN_CHANGE = "screenChange"
    HANDLE_TRANSCRIBED_TEXT = "transcribedText"
    
    # Task methods
    HANDLE_TASK_START = "startTask"
    HANDLE_TASK_END = "endTask"
    HANDLE_TASK_SKIP = "skipTask"

class RPCHandlerType(str, Enum):
    """Types of RPC handlers"""
    INTERACTION = "interaction"
    TASK = "task"

class RPCResponse(TypedDict, total=False):
    """Standard RPC response format"""
    success: bool
    message: Optional[str]
    data: Optional[Dict[str, Any]]

class ComponentClickPayload(TypedDict, total=False):
    """Payload for component click RPC"""
    tenantId: str
    fileKey: str
    frameId: str
    nodeId: str
    newFrameId: Optional[str]
    timestamp: int
    animation: bool = False
    coordinates: Dict[str, float]
    taskNumber: int

class ScreenChangePayload(TypedDict, total=False):
    """Payload for screen change RPC"""
    tenantId: str
    fileKey: str
    frameId: str
    timestamp: int
    taskNumber: int

class TranscribedTextPayload(TypedDict, total=False):
    """Payload for transcribed text RPC"""
    transcribedText: str
    timestamp: int

class TaskStartPayload(TypedDict, total=False):
    """Payload for task start RPC"""
    taskNumber: int
    taskName: str
    taskDescription: str
    taskInstructions: str
    timestamp: int

class TaskEndPayload(TypedDict, total=False):
    """Payload for task end RPC"""
    taskNumber: int
    timestamp: int

class TaskSkipPayload(TypedDict, total=False):
    """Payload for task skip RPC"""
    taskNumber: int
    timestamp: int 