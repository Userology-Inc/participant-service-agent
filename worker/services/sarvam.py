from typing import List, Dict, Union, Optional, Any, Tuple
import requests
import base64
from enum import Enum
import os


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


class SarvamAI:
    """Client for the Sarvam.AI TTS and STT APIs"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.sarvam.ai"):
        """Initialize the SarvamAI client
        
        Args:
            api_key: Your Sarvam API subscription key
            base_url: Optional base URL for the Sarvam API
        """
        if not api_key:
            raise ValueError("API subscription key is required")
        
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
    
    def text_to_speech(
        self,
        text: Union[str, List[str]],
        language_code: LanguageCode,
        speaker: Optional[TTSSpeaker] = None,
        pitch: Optional[float] = None,
        pace: Optional[float] = None,
        loudness: Optional[float] = None,
        sample_rate: Optional[TTSSampleRate] = None,
        enable_preprocessing: Optional[bool] = None,
        model: Optional[TTSModel] = None,
        eng_interpolation_wt: Optional[float] = None,
        override_triplets: Optional[Dict[str, Any]] = None
    ) -> TTSResponse:
        """Convert text to speech
        
        Args:
            text: Text(s) to convert to speech (string or list of strings)
            language_code: Language of the input text
            speaker: Voice to use for synthesis
            pitch: Voice pitch adjustment (-0.75 to 0.75)
            pace: Speaking pace adjustment (0.5 to 2.0)
            loudness: Audio loudness adjustment (0.3 to 3.0)
            sample_rate: Output audio sample rate
            enable_preprocessing: Enable text preprocessing
            model: TTS model to use
            eng_interpolation_wt: Weight for interpolating with English speaker
            override_triplets: Custom speaker triplets
            
        Returns:
            TTSResponse object containing the generated audio
            
        Raises:
            ValueError: For invalid parameter values
            requests.RequestException: For API request failures
        """
        # Convert string to list if necessary
        if isinstance(text, str):
            inputs = [text]
        else:
            inputs = text
            
        # Input validation
        if not inputs:
            raise ValueError("At least one input text is required")
        
        if len(inputs) > 3:
            raise ValueError("Maximum 3 input texts are allowed")
            
        if any(len(t) > 500 for t in inputs):
            raise ValueError("Each text should be no longer than 500 characters")
            
        if pitch is not None and (pitch < -0.75 or pitch > 0.75):
            raise ValueError("Pitch must be between -0.75 and 0.75")
            
        if pace is not None and (pace < 0.5 or pace > 2.0):
            raise ValueError("Pace must be between 0.5 and 2.0")
            
        if loudness is not None and (loudness < 0.3 or loudness > 3.0):
            raise ValueError("Loudness must be between 0.3 and 3.0")
            
        # Build request payload
        payload = {
            "inputs": inputs,
            "target_language_code": language_code.value if isinstance(language_code, LanguageCode) else language_code
        }
        
        if speaker is not None:
            payload["speaker"] = speaker.value if isinstance(speaker, TTSSpeaker) else speaker
        if pitch is not None:
            payload["pitch"] = pitch
        if pace is not None:
            payload["pace"] = pace
        if loudness is not None:
            payload["loudness"] = loudness
        if sample_rate is not None:
            payload["speech_sample_rate"] = (
                sample_rate.value if isinstance(sample_rate, TTSSampleRate) else sample_rate
            )
        if enable_preprocessing is not None:
            payload["enable_preprocessing"] = enable_preprocessing
        if model is not None:
            payload["model"] = model.value if isinstance(model, TTSModel) else model
        if eng_interpolation_wt is not None:
            payload["eng_interpolation_wt"] = eng_interpolation_wt
        if override_triplets is not None:
            payload["override_triplets"] = override_triplets
            
        # Make API request
        response = requests.post(
            f"{self.base_url}/text-to-speech",
            headers={
                "api-subscription-key": self.api_key,
                "Content-Type": "application/json"
            },
            json=payload
        )
        
        # Handle errors
        if not response.ok:
            try:
                error_data = response.json()
                error_msg = f"TTS API error ({response.status_code}): {error_data}"
            except:
                error_msg = f"TTS API error ({response.status_code}): {response.text}"
            raise requests.RequestException(error_msg)
            
        # Parse and return response
        return TTSResponse.from_dict(response.json())
    
    def speech_to_text(
        self,
        audio_file: Union[str, bytes, Any],  # Path, bytes or file-like object
        model: Optional[STTModel] = None,
        language_code: Optional[LanguageCode] = None,
        with_timestamps: Optional[bool] = None,
        with_diarization: Optional[bool] = None,
        num_speakers: Optional[int] = None
    ) -> STTResponse:
        """Convert speech to text
        
        Args:
            audio_file: Path to audio file, bytes, or file-like object.
                        Can also be a tuple of (filename, file, content_type)
            model: STT model to use. Default is saarika:v2 if not specified.
                   Options: saarika:v1, saarika:v2, saarika:flash
            language_code: Language of the input audio. Required for saarika:v1 model.
                           Optional for saarika:v2 model. Use "unknown" for auto-detection.
            with_timestamps: Include timestamps in response
            with_diarization: Enable speaker diarization (Beta feature)
            num_speakers: Number of speakers for diarization
            
        Returns:
            STTResponse object containing the transcription
            
        Raises:
            ValueError: For invalid parameter values
            requests.RequestException: For API request failures
        """
        # Prepare file parameter based on input type
        should_close = False
        
        if isinstance(audio_file, tuple) and len(audio_file) == 3:
            # Handle (filename, file, content_type) tuple format
            filename, file_obj, content_type = audio_file
            files = {'file': (filename, file_obj, content_type)}
        elif isinstance(audio_file, str):  # Path to file
            files = {'file': open(audio_file, 'rb')}
            should_close = True
        elif isinstance(audio_file, bytes):  # Bytes
            files = {'file': ('audio.wav', audio_file, 'audio/wav')}
        else:  # File-like object
            files = {'file': audio_file}
        
        # Validation
        if model == STTModel.SAARIKA_V1 and (language_code is None or language_code == LanguageCode.UNKNOWN):
            raise ValueError("language_code is required when using saarika:v1 model, and cannot be 'unknown'")
            
        # Prepare form data
        data = {}
        if model is not None:
            data['model'] = model.value if isinstance(model, STTModel) else model
        if language_code is not None:
            data['language_code'] = language_code.value if isinstance(language_code, LanguageCode) else language_code
        if with_timestamps is not None:
            data['with_timestamps'] = str(with_timestamps).lower()
        if with_diarization is not None:
            data['with_diarization'] = str(with_diarization).lower()
        if num_speakers is not None:
            data['num_speakers'] = str(num_speakers)
            
        try:
            # Make API request
            response = requests.post(
                f"{self.base_url}/speech-to-text",
                headers={"api-subscription-key": self.api_key},
                files=files,
                data=data
            )
            
            # Handle errors
            if not response.ok:
                try:
                    error_data = response.json()
                    error_msg = f"STT API error ({response.status_code}): {error_data}"
                except:
                    error_msg = f"STT API error ({response.status_code}): {response.text}"
                raise requests.RequestException(error_msg)
                
            # Parse and return response
            return STTResponse.from_dict(response.json())
        finally:
            # Close file if we opened it
            if should_close and isinstance(audio_file, str) and 'file' in files:
                files['file'].close()
    
    @staticmethod
    def get_tts_languages() -> List[LanguageCode]:
        """Returns the list of supported languages for Text-to-Speech"""
        return [
            LanguageCode.HINDI, LanguageCode.BENGALI, LanguageCode.KANNADA,
            LanguageCode.MALAYALAM, LanguageCode.MARATHI, LanguageCode.ODIA,
            LanguageCode.PUNJABI, LanguageCode.TAMIL, LanguageCode.TELUGU,
            LanguageCode.ENGLISH, LanguageCode.GUJARATI
        ]
    
    @staticmethod
    def get_tts_models() -> List[TTSModel]:
        """Returns the list of supported models for Text-to-Speech"""
        return [TTSModel.BULBUL_V1]
    
    @staticmethod
    def get_tts_speakers() -> List[TTSSpeaker]:
        """Returns the list of available speakers for Text-to-Speech"""
        return list(TTSSpeaker)
    
    @staticmethod
    def get_stt_languages() -> List[LanguageCode]:
        """Returns the list of supported languages for Speech-to-Text"""
        return [
            LanguageCode.HINDI, LanguageCode.BENGALI, LanguageCode.KANNADA,
            LanguageCode.MALAYALAM, LanguageCode.MARATHI, LanguageCode.ODIA,
            LanguageCode.PUNJABI, LanguageCode.TAMIL, LanguageCode.TELUGU,
            LanguageCode.ENGLISH, LanguageCode.GUJARATI
        ]
    
    @staticmethod
    def get_stt_models() -> List[STTModel]:
        """Returns the list of supported models for Speech-to-Text"""
        return list(STTModel)
    
    @staticmethod
    def get_tts_sample_rates() -> List[TTSSampleRate]:
        """Returns the supported sample rates for Text-to-Speech"""
        return list(TTSSampleRate)
