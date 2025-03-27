from typing import List, Dict, Union, Optional, Any, Tuple
import base64
import os
from enum import Enum


class LanguageCode(str, Enum):
    """Language codes supported by Sarvam TTS and STT"""
    HINDI = "hi-IN"
    BENGALI = "bn-IN"
    KANNADA = "kn-IN"
    MALAYALAM = "ml-IN"
    MARATHI = "mr-IN"
    ODIA = "od-IN"
    PUNJABI = "pa-IN"
    TAMIL = "ta-IN"
    TELUGU = "te-IN"
    ENGLISH = "en-IN"
    GUJARATI = "gu-IN"
    UNKNOWN = "unknown"


class TTSSpeaker(str, Enum):
    """Speakers available for Text-to-Speech"""
    MEERA = "meera"
    PAVITHRA = "pavithra"
    MAITREYI = "maitreyi"
    ARVIND = "arvind"
    AMOL = "amol"
    AMARTYA = "amartya"
    DIYA = "diya"
    NEEL = "neel"
    MISHA = "misha"
    VIAN = "vian"
    ARJUN = "arjun"
    MAYA = "maya"


class TTSModel(str, Enum):
    """Models available for Text-to-Speech"""
    BULBUL_V1 = "bulbul:v1"


class STTModel(str, Enum):
    """Models available for Speech-to-Text"""
    SAARIKA_V1 = "saarika:v1"
    SAARIKA_V2 = "saarika:v2"
    SAARIKA_FLASH = "saarika:flash"


class TTSSampleRate(int, Enum):
    """Supported sample rates for Text-to-Speech"""
    LOW = 8000
    MEDIUM = 16000
    HIGH = 22050


class TranslationMode(str, Enum):
    """Translation modes supported by Sarvam Translation API"""
    FORMAL = "formal"
    MODERN_COLLOQUIAL = "modern-colloquial"
    CLASSIC_COLLOQUIAL = "classic-colloquial"
    CODE_MIXED = "code-mixed"


class SpeakerGender(str, Enum):
    """Speaker gender options for translation"""
    MALE = "Male"
    FEMALE = "Female"


class OutputScript(str, Enum):
    """Output script options for translation"""
    ROMAN = "roman"
    FULLY_NATIVE = "fully-native"
    SPOKEN_FORM_IN_NATIVE = "spoken-form-in-native"


class NumeralsFormat(str, Enum):
    """Numerals format options for translation"""
    INTERNATIONAL = "international"
    NATIVE = "native"


class TTSResponse:
    """Text-to-Speech response object"""
    
    def __init__(self, request_id: Optional[str], audios: List[str]):
        self.request_id = request_id
        self.audios = audios
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TTSResponse':
        """Create a TTSResponse instance from a dictionary"""
        return cls(
            request_id=data.get("request_id"),
            audios=data.get("audios", [])
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the TTSResponse instance to a dictionary"""
        return {
            "request_id": self.request_id,
            "audios": self.audios
        }
    
    def save_audio_files(self, directory: str = ".", prefix: str = "audio") -> List[str]:
        """Save the base64 audios to WAV files
        
        Args:
            directory: Directory to save the files in
            prefix: Prefix for the filenames
            
        Returns:
            List of file paths that were created
        """
        os.makedirs(directory, exist_ok=True)
        file_paths = []
        
        for i, audio_base64 in enumerate(self.audios):
            file_path = os.path.join(directory, f"{prefix}_{i}.wav")
            with open(file_path, "wb") as f:
                f.write(base64.b64decode(audio_base64))
            file_paths.append(file_path)
            
        return file_paths


class STTResponse:
    """Speech-to-Text response object"""
    
    def __init__(
        self, 
        request_id: Optional[str], 
        transcript: str,
        timestamps: Optional[Dict[str, Any]] = None,
        diarized_transcript: Optional[Dict[str, Any]] = None,
        language_code: Optional[str] = None
    ):
        self.request_id = request_id
        self.transcript = transcript
        self.timestamps = timestamps
        self.diarized_transcript = diarized_transcript
        self.language_code = language_code
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'STTResponse':
        """Create an STTResponse instance from a dictionary"""
        return cls(
            request_id=data.get("request_id"),
            transcript=data.get("transcript", ""),
            timestamps=data.get("timestamps"),
            diarized_transcript=data.get("diarized_transcript"),
            language_code=data.get("language_code")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the STTResponse instance to a dictionary"""
        result = {
            "request_id": self.request_id,
            "transcript": self.transcript
        }
        
        if self.timestamps:
            result["timestamps"] = self.timestamps
        if self.diarized_transcript:
            result["diarized_transcript"] = self.diarized_transcript
        if self.language_code:
            result["language_code"] = self.language_code
            
        return result


class TranslationResponse:
    """Translation response object"""
    
    def __init__(self, request_id: Optional[str], translated_text: str):
        self.request_id = request_id
        self.translated_text = translated_text
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TranslationResponse':
        """Create a TranslationResponse instance from a dictionary"""
        return cls(
            request_id=data.get("request_id"),
            translated_text=data.get("translated_text", "")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the TranslationResponse instance to a dictionary"""
        return {
            "request_id": self.request_id,
            "translated_text": self.translated_text
        }
