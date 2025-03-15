from __future__ import annotations

import dataclasses
import os
import tempfile
from dataclasses import dataclass
from typing import Optional

from livekit import rtc
from livekit.agents import (
    APIConnectionError,
    APIConnectOptions,
    APIStatusError,
    APITimeoutError,
    stt,
)
from livekit.agents.utils import AudioBuffer

from worker.services.sarvam import (
    LanguageCode,
    SarvamAI,
    STTModel,
)

from .log import logger


@dataclass
class _STTOptions:
    language_code: LanguageCode | str
    detect_language: bool
    model: STTModel | str
    with_timestamps: bool
    with_diarization: bool
    num_speakers: Optional[int]


class STT(stt.STT):
    def __init__(
        self,
        *,
        language_code: LanguageCode | str = LanguageCode.ENGLISH,
        detect_language: bool = False,
        model: STTModel | str = STTModel.SAARIKA_V2,
        with_timestamps: bool = False,
        with_diarization: bool = False,
        num_speakers: Optional[int] = None,
        api_key: str | None = None,
        base_url: str | None = None,
        client: SarvamAI | None = None,
    ):
        """
        Create a new instance of Sarvam STT.

        ``api_key`` must be set to your Sarvam API key, either using the argument or by setting the
        ``SARVAM_API_KEY`` environmental variable.
        """

        super().__init__(
            capabilities=stt.STTCapabilities(streaming=False, interim_results=False)
        )
        
        if detect_language:
            language_code = LanguageCode.UNKNOWN

        self._opts = _STTOptions(
            language_code=language_code,
            detect_language=detect_language,
            model=model,
            with_timestamps=with_timestamps,
            with_diarization=with_diarization,
            num_speakers=num_speakers,
        )

        api_key = api_key or os.environ.get("SARVAM_API_KEY")
        if api_key is None and client is None:
            raise ValueError("Sarvam API key is required")

        self._client = client or SarvamAI(
            api_key=api_key,
            base_url=base_url or "https://api.sarvam.ai",
        )

    def update_options(
        self,
        *,
        model: STTModel | str | None = None,
        language_code: LanguageCode | str | None = None,
        with_timestamps: Optional[bool] = None,
        with_diarization: Optional[bool] = None,
        num_speakers: Optional[int] = None,
    ) -> None:
        """Update the STT options."""
        if model is not None:
            self._opts.model = model
        if language_code is not None:
            self._opts.language_code = language_code
            self._opts.detect_language = language_code == LanguageCode.UNKNOWN
        if with_timestamps is not None:
            self._opts.with_timestamps = with_timestamps
        if with_diarization is not None:
            self._opts.with_diarization = with_diarization
        if num_speakers is not None:
            self._opts.num_speakers = num_speakers

    def _sanitize_options(self, *, language_code: str | None = None) -> _STTOptions:
        config = dataclasses.replace(self._opts)
        if language_code is not None:
            config.language_code = language_code
            config.detect_language = language_code == LanguageCode.UNKNOWN
        return config

    async def _recognize_impl(
        self,
        buffer: AudioBuffer,
        *,
        language: str | None,
        conn_options: APIConnectOptions,
    ) -> stt.SpeechEvent:
        try:
            config = self._sanitize_options(language_code=language)
            
            # Convert audio buffer to WAV bytes
            audio_data = rtc.combine_audio_frames(buffer).to_wav_bytes()
            
            # Call Sarvam STT API directly with the audio data as bytes
            # This avoids filesystem operations and temporary files
            try:
                resp = self._client.speech_to_text(
                    audio_file=('audio.wav', audio_data, 'audio/wav'),
                    model=config.model,
                    language_code=config.language_code if not config.detect_language else None,
                    with_timestamps=config.with_timestamps,
                    with_diarization=config.with_diarization,
                    num_speakers=config.num_speakers,
                )
                
                print("resp->", resp)

                # Create speech event from response
                return stt.SpeechEvent(
                    type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                    alternatives=[
                        stt.SpeechData(
                            text=resp.transcript or "",
                            language=resp.language_code or str(config.language_code),
                            # start_time=resp.timestamps.timestamps.start_time_seconds[0],
                            # end_time=resp.timestamps.timestamps.end_time_seconds[0],
                        )
                    ],
                )
            except Exception as e:
                logger.warning(f"Failed to transcribe audio: {e}")
                raise

        except Exception as e:
            if "timeout" in str(e).lower():
                raise APITimeoutError()
            elif hasattr(e, "status_code"):
                raise APIStatusError(
                    str(e),
                    status_code=getattr(e, "status_code", 500),
                    request_id=getattr(e, "request_id", None),
                    body=getattr(e, "body", None),
                )
            else:
                raise APIConnectionError() from e