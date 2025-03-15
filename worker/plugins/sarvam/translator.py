import os
import logging
from typing import Optional, Union

from worker.services.sarvam import (
    SarvamAI, 
    LanguageCode, 
    TranslationMode,
    SpeakerGender,
    OutputScript,
    NumeralsFormat
)

logger = logging.getLogger(__name__)


class Translator:
    """Sarvam Translation plugin for LiveKit Agents"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        speaker_gender: Optional[Union[SpeakerGender, str]] = None,
        mode: Optional[Union[TranslationMode, str]] = None,
        enable_preprocessing: Optional[bool] = None,
        output_script: Optional[Union[OutputScript, str]] = None,
        numerals_format: Optional[Union[NumeralsFormat, str]] = None
    ):
        """Initialize Sarvam Translator plugin
        
        Args:
            api_key: Sarvam API key (defaults to SARVAM_API_KEY env var)
            speaker_gender: Gender of the speaker (for better translations)
            mode: Translation mode (formal, modern-colloquial, etc.)
            enable_preprocessing: Enable custom preprocessing of input text
            output_script: Transliteration style for output text
            numerals_format: Format for numerals in output text
        """
        self.api_key = api_key or os.environ.get("SARVAM_API_KEY")
        if not self.api_key:
            raise ValueError("Sarvam API key is required. Set SARVAM_API_KEY env var or pass api_key.")
            
        self.speaker_gender = speaker_gender
        self.mode = mode
        self.enable_preprocessing = enable_preprocessing
        self.output_script = output_script
        self.numerals_format = numerals_format
        
        self.client = SarvamAI(api_key=self.api_key)
        
    def translate(
        self, 
        text: str, 
        source_language: Union[LanguageCode, str], 
        target_language: Union[LanguageCode, str]
    ) -> str:
        """Translate text from one language to another
        
        Args:
            text: Text to translate
            source_language: Source language code
            target_language: Target language code
            
        Returns:
            Translated text
        """
        try:
            response = self.client.translate_text(
                input_text=text,
                source_language_code=source_language,
                target_language_code=target_language,
                speaker_gender=self.speaker_gender,
                mode=self.mode,
                enable_preprocessing=self.enable_preprocessing,
                output_script=self.output_script,
                numerals_format=self.numerals_format
            )
            
            return response.translated_text
        except Exception as e:
            logger.exception(f"Error in Sarvam Translator: {e}")
            raise 