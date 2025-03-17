from enum import Enum

class ExternalMessageType(str, Enum):
    """Types of external messages that can be received"""
    SECTION_START = "SectionStart"
    SECTION_END = "SectionEnd"
    SECTION_SKIP = "SectionSkip"
    INTERACTION = "Interaction"
    SCREEN_SHARE = "ScreenShare"
    TASK = "Task"
    OTHER = "Other" 


