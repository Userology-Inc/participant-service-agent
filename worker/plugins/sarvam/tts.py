from __future__ import annotations

import asyncio
import base64
import os
from dataclasses import dataclass
from typing import Optional

from livekit.agents import (
    APIConnectionError,
    APIConnectOptions,
    APIStatusError,
    APITimeoutError,
    tts,
    utils,
)

from worker.services.sarvam import (
    LanguageCode,
    SarvamAI,
    TTSModel,
    TTSSampleRate,
    TTSSpeaker,
)

from .log import logger

# Sarvam TTS outputs at 22050 Hz by default
SARVAM_TTS_SAMPLE_RATE = 22050
SARVAM_TTS_CHANNELS = 1


@dataclass
class _TTSOptions:
    model: TTSModel | str
    speaker: TTSSpeaker | str
    language_code: LanguageCode | str
    pitch: Optional[float] = None
    pace: Optional[float] = None
    loudness: Optional[float] = None
    sample_rate: Optional[TTSSampleRate] = None
    enable_preprocessing: Optional[bool] = None


class TTS(tts.TTS):
    def __init__(
        self,
        *,
        model: TTSModel | str = TTSModel.BULBUL_V1,
        speaker: TTSSpeaker | str = TTSSpeaker.MEERA,
        language_code: LanguageCode | str = LanguageCode.ENGLISH,
        pitch: Optional[float] = None,
        pace: Optional[float] = None,
        loudness: Optional[float] = None,
        sample_rate: Optional[TTSSampleRate] = None,
        enable_preprocessing: Optional[bool] = None,
        api_key: str | None = None,
        base_url: str | None = None,
        client: SarvamAI | None = None,
    ) -> None:
        """
        Create a new instance of Sarvam TTS.

        ``api_key`` must be set to your Sarvam API key, either using the argument or by setting the
        ``SARVAM_API_KEY`` environmental variable.
        """

        super().__init__(
            capabilities=tts.TTSCapabilities(
                streaming=False,
            ),
            sample_rate=SARVAM_TTS_SAMPLE_RATE,
            num_channels=SARVAM_TTS_CHANNELS,
        )

        self._opts = _TTSOptions(
            model=model,
            speaker=speaker,
            language_code=language_code,
            pitch=pitch,
            pace=pace,
            loudness=loudness,
            sample_rate=sample_rate,
            enable_preprocessing=enable_preprocessing,
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
        model: TTSModel | str | None = None,
        speaker: TTSSpeaker | str | None = None,
        language_code: LanguageCode | str | None = None,
        pitch: Optional[float] = None,
        pace: Optional[float] = None,
        loudness: Optional[float] = None,
        sample_rate: Optional[TTSSampleRate] = None,
        enable_preprocessing: Optional[bool] = None,
    ) -> None:
        """Update the TTS options."""
        if model is not None:
            self._opts.model = model
        if speaker is not None:
            self._opts.speaker = speaker
        if language_code is not None:
            self._opts.language_code = language_code
        if pitch is not None:
            self._opts.pitch = pitch
        if pace is not None:
            self._opts.pace = pace
        if loudness is not None:
            self._opts.loudness = loudness
        if sample_rate is not None:
            self._opts.sample_rate = sample_rate
        if enable_preprocessing is not None:
            self._opts.enable_preprocessing = enable_preprocessing

    def synthesize(
        self,
        text: str,
        *,
        conn_options: Optional[APIConnectOptions] = None,
    ) -> "ChunkedStream":
        return ChunkedStream(
            tts=self,
            input_text=text,
            conn_options=conn_options,
            opts=self._opts,
            client=self._client,
        )


class ChunkedStream(tts.ChunkedStream):
    def __init__(
        self,
        *,
        tts: TTS,
        input_text: str,
        conn_options: Optional[APIConnectOptions] = None,
        opts: _TTSOptions,
        client: SarvamAI,
    ) -> None:
        super().__init__(tts=tts, input_text=input_text, conn_options=conn_options)
        self._client = client
        self._opts = opts

    async def _run(self):
        request_id = utils.shortuuid()
        decoder = utils.codecs.AudioStreamDecoder(
            sample_rate=SARVAM_TTS_SAMPLE_RATE,
            num_channels=SARVAM_TTS_CHANNELS,
        )

        try:
            # Call Sarvam TTS API
            response = self._client.text_to_speech(
                text=self.input_text,
                language_code=self._opts.language_code,
                speaker=self._opts.speaker,
                pitch=self._opts.pitch,
                pace=self._opts.pace,
                loudness=self._opts.loudness,
                sample_rate=self._opts.sample_rate,
                enable_preprocessing=self._opts.enable_preprocessing,
                model=self._opts.model,
            )

            # Process the audio data
            if not response.audios or len(response.audios) == 0:
                raise APIConnectionError("No audio data received from Sarvam API")

            # Decode the base64 audio data
            for audio_base64 in response.audios:
                audio_data = base64.b64decode(audio_base64)
                decoder.push(audio_data)
            
            decoder.end_input()

            # Emit the audio frames
            emitter = tts.SynthesizedAudioEmitter(
                event_ch=self._event_ch,
                request_id=request_id,
            )
            
            async for frame in decoder:
                emitter.push(frame)
            
            emitter.flush()

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
        finally:
            await decoder.aclose()
