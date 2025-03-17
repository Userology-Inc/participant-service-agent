from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class Word:
    """Word with timing information"""
    text: str
    start: float
    end: float

@dataclass
class TimedTranscript:
    """Transcript with timing information"""
    type: str
    role: str
    content: str
    start: float
    end: float
    words: List[Word]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "type": self.type,
            "role": self.role,
            "content": self.content,
            "start": self.start,
            "end": self.end,
            "words": [
                {"text": word.text, "start": word.start, "end": word.end}
                for word in self.words
            ]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TimedTranscript':
        """Create from dictionary"""
        return cls(
            type=data.get("type", "transcript"),
            role=data.get("role", "user"),
            content=data.get("content", ""),
            start=data.get("start", 0.0),
            end=data.get("end", 0.0),
            words=[
                Word(
                    text=word.get("text", ""),
                    start=word.get("start", 0.0),
                    end=word.get("end", 0.0)
                )
                for word in data.get("words", [])
            ]
        ) 