from __future__ import annotations

import dataclasses
import os
from dataclasses import dataclass
from typing import Optional, List

from livekit import rtc
from livekit.agents import (
    APIConnectionError,
    APIConnectOptions,
    APIStatusError,
    APITimeoutError,
    stt,
)
from livekit.agents.utils import AudioBuffer

from elevenlabs.client import ElevenLabs
from elevenlabs.types.speech_to_text_chunk_response_model import SpeechToTextChunkResponseModel
from elevenlabs.types.speech_to_text_word_response_model import SpeechToTextWordResponseModel
from elevenlabs.types.speech_to_text_character_response_model import SpeechToTextCharacterResponseModel
from .log import logger



@dataclass
class STTOptions:
    model_id: str
    language_code: str
    tag_audio_events: bool
    diarize: bool
    biased_keywords: Optional[List[str]] = None
    timestamps_granularity: Optional[str] = None
    num_speakers: Optional[int] = None


class STT(stt.STT):
    def __init__(
        self,
        *,
        model_id: str = "scribe_v1",
        language_code: str = "eng",
        tag_audio_events: bool = True,
        diarize: bool = False,
        biased_keywords: Optional[List[str]] = None,
        timestamps_granularity: Optional[str] = 'character', # Enum of  timestamps_granularity?: 'none' | 'word' | 'character'; 
        num_speakers: Optional[int] = None,
        api_key: Optional[str] = None,
        client: Optional[ElevenLabs] = None,
    ):
        """
        Create a new instance of ElevenLabs STT.

        Args:
            model_id (str): Model to use, currently only "scribe_v1" is supported
            language_code (str): Language of the audio file. If not set, the model will detect the language automatically
            tag_audio_events (bool): Tag audio events like laughter, applause, etc.
            diarize (bool): Whether to annotate who is speaking
            biased_keywords (List[str]): List of keywords to bias towards in transcription
            timestamps_granularity (str): Granularity of timestamps ('none', 'word', or 'character')
            num_speakers (int): Expected number of speakers in the audio
            api_key (str): ElevenLabs API key. Can also be set via ELEVENLABS_API_KEY env var
            client (ElevenLabs): Optional pre-configured ElevenLabs client
        """
        super().__init__(
            capabilities=stt.STTCapabilities(streaming=False, interim_results=False)
        )

        self._api_key = api_key or os.environ.get("ELEVENLABS_API_KEY")
        if not self._api_key and not client:
            raise ValueError(
                "ElevenLabs API key is required. Pass it via api_key parameter or set ELEVENLABS_API_KEY environment variable."
            )

        self._opts = STTOptions(
            model_id=model_id,
            language_code=language_code,
            tag_audio_events=tag_audio_events,
            diarize=diarize,
            biased_keywords=biased_keywords,
            timestamps_granularity=timestamps_granularity,
            num_speakers=num_speakers,
        )

        self._client = client or ElevenLabs(api_key=self._api_key)

    def update_options(
        self,
        *,
        model_id: Optional[str] = None,
        language_code: Optional[str] = None,
        tag_audio_events: Optional[bool] = None,
        diarize: Optional[bool] = None,
        biased_keywords: Optional[List[str]] = None,
        timestamps_granularity: Optional[str] = None,
        num_speakers: Optional[int] = None,
    ) -> None:
        """Update the STT options."""
        if model_id is not None:
            self._opts.model_id = model_id
        if language_code is not None:
            self._opts.language_code = language_code
        if tag_audio_events is not None:
            self._opts.tag_audio_events = tag_audio_events
        if diarize is not None:
            self._opts.diarize = diarize
        if biased_keywords is not None:
            self._opts.biased_keywords = biased_keywords
        if timestamps_granularity is not None:
            self._opts.timestamps_granularity = timestamps_granularity
        if num_speakers is not None:
            self._opts.num_speakers = num_speakers

    def _sanitize_options(self, *, language: str | None = None) -> STTOptions:
        """Sanitize and validate the options."""
        config = dataclasses.replace(self._opts)
        if language:
            config.language_code = language
            
        # Format biased keywords if they exist
        if config.biased_keywords:
            formatted_keywords = []
            for keyword in config.biased_keywords:
                if ':' in keyword:
                    parts = keyword.split(':', 1)
                    if len(parts) == 2:
                        word = parts[0].strip()
                        bias_str = parts[1].strip()
                        if word and bias_str:
                            try:
                                float(bias_str)
                                formatted_keywords.append(f"{word}:{bias_str}")
                            except ValueError:
                                formatted_keywords.append(f"{word}:1.0")
                        else:
                            formatted_keywords.append(f"{keyword.replace(':', '').strip()}:1.0")
                    else:
                        formatted_keywords.append(f"{keyword.replace(':', '').strip()}:1.0")
                else:
                    formatted_keywords.append(f"{keyword.strip()}:1.0")
            config.biased_keywords = formatted_keywords
            
        return config

    async def _recognize_impl(
        self,
        buffer: AudioBuffer,
        *,
        language: str | None,
        conn_options: APIConnectOptions,
    ) -> stt.SpeechEvent:
        """Implement the recognition logic using ElevenLabs API."""
        try:
            config = self._sanitize_options(language=language)
            audio_data = rtc.combine_audio_frames(buffer).to_wav_bytes()

            # Convert the audio data to a BytesIO object as expected by ElevenLabs
            from io import BytesIO
            audio_data_io = BytesIO(audio_data)

            # Call ElevenLabs API
            transcription: SpeechToTextChunkResponseModel = self._client.speech_to_text.convert(
                file=audio_data_io,
                model_id=config.model_id,
                language_code=config.language_code,
                tag_audio_events=config.tag_audio_events,
                diarize=config.diarize,
                timestamps_granularity=config.timestamps_granularity,
                # biased_keywords=config.biased_keywords,
                # num_speakers=config.num_speakers,
            )
            
            logger.info(f"transcription: {transcription}")

            # Helper functions with proper type annotations
            def process_character(char: SpeechToTextCharacterResponseModel) -> stt.SpeechCharacter:
                return stt.SpeechCharacter(
                    text=char.text,
                    start=char.start,
                    end=char.end,
                )
            
            def process_word(word: SpeechToTextWordResponseModel) -> stt.SpeechWord:
                return stt.SpeechWord(
                    text=word.text, 
                    start=word.start, 
                    end=word.end, 
                    characters=[process_character(char) for char in (word.characters or [])],
                    type=word.type
                )

            # Convert ElevenLabs response to LiveKit SpeechEvent format
            return stt.SpeechEvent(
                type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                alternatives=[
                    stt.SpeechData(
                        text=transcription.text,
                        language=config.language_code,
                        language_probability=transcription.language_probability,
                        words=[process_word(word) for word in transcription.words],
                    )
                ],
            )

        except Exception as e:
            # Handle specific ElevenLabs exceptions and convert to LiveKit exceptions
            if "timeout" in str(e).lower():
                raise APITimeoutError() from e
            if hasattr(e, "status_code"):
                raise APIStatusError(
                    message=str(e),
                    status_code=getattr(e, "status_code", 500),
                    request_id=None,
                    body=None,
                ) from e
            raise APIConnectionError() from e 