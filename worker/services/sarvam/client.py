import requests
from typing import List, Dict, Union, Optional, Any, Tuple

from worker.services.sarvam.types import (
    LanguageCode, TTSSpeaker, TTSModel, STTModel, TTSSampleRate,
    TranslationMode, SpeakerGender, OutputScript, NumeralsFormat,
    TTSResponse, STTResponse, TranslationResponse
)
from worker.services.sarvam.log import logger


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
        logger.debug(f"Initialized SarvamAI client with base URL: {self.base_url}")
    
    def translate_text(
        self,
        input_text: str,
        source_language_code: LanguageCode,
        target_language_code: LanguageCode,
        speaker_gender: Optional[SpeakerGender] = None,
        mode: Optional[TranslationMode] = None,
        enable_preprocessing: Optional[bool] = None,
        output_script: Optional[OutputScript] = None,
        numerals_format: Optional[NumeralsFormat] = None
    ) -> TranslationResponse:
        """Translate text from one language to another
        
        Args:
            input_text: The text to translate
            source_language_code: The language code of the input text
            target_language_code: The language code to translate to
            speaker_gender: Gender of the speaker (for better translations)
            mode: Translation mode (formal, modern-colloquial, etc.)
            enable_preprocessing: Enable custom preprocessing of input text
            output_script: Transliteration style for output text
            numerals_format: Format for numerals in output text
            
        Returns:
            TranslationResponse object containing the translated text
            
        Raises:
            ValueError: For invalid parameter values
            requests.RequestException: For API request failures
        """
        # Input validation
        if not input_text:
            raise ValueError("Input text is required")
            
        if len(input_text) > 1000:
            raise ValueError("Input text should be no longer than 1000 characters")
            
        # Build request payload
        payload = {
            "input": input_text,
            "source_language_code": source_language_code.value if isinstance(source_language_code, LanguageCode) else source_language_code,
            "target_language_code": target_language_code.value if isinstance(target_language_code, LanguageCode) else target_language_code
        }
        
        if speaker_gender is not None:
            payload["speaker_gender"] = speaker_gender.value if isinstance(speaker_gender, SpeakerGender) else speaker_gender
        if mode is not None:
            payload["mode"] = mode.value if isinstance(mode, TranslationMode) else mode
        if enable_preprocessing is not None:
            payload["enable_preprocessing"] = enable_preprocessing
        if output_script is not None:
            payload["output_script"] = output_script.value if isinstance(output_script, OutputScript) else output_script
        if numerals_format is not None:
            payload["numerals_format"] = numerals_format.value if isinstance(numerals_format, NumeralsFormat) else numerals_format
            
        logger.debug(f"Making translation API request with payload: {payload}")
            
        # Make API request
        response = requests.post(
            f"{self.base_url}/translate",
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
                error_msg = f"Translation API error ({response.status_code}): {error_data}"
            except:
                error_msg = f"Translation API error ({response.status_code}): {response.text}"
            logger.error(error_msg)
            raise requests.RequestException(error_msg)
            
        # Parse and return response
        response_data = response.json()
        logger.debug(f"Translation API response: {response_data}")
        return TranslationResponse.from_dict(response_data)
    
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
            
        logger.debug(f"Making TTS API request with payload: {payload}")
            
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
            logger.error(error_msg)
            raise requests.RequestException(error_msg)
            
        # Parse and return response
        response_data = response.json()
        logger.debug(f"TTS API response received with {len(response_data.get('audios', []))} audio(s)")
        return TTSResponse.from_dict(response_data)
    
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
            
        logger.debug(f"Making STT API request with data: {data}")
            
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
                logger.error(error_msg)
                raise requests.RequestException(error_msg)
                
            # Parse and return response
            response_data = response.json()
            logger.debug(f"STT API response received with transcript of length {len(response_data.get('transcript', ''))}")
            return STTResponse.from_dict(response_data)
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
