from .stt import STT

def example_usage():
    # Initialize STT with default options
    stt = STT(
        model_id="scribe_v1",
        language_code="eng",
        tag_audio_events=True,
        diarize=False,
        api_key="your-api-key"  # Or set ELEVENLABS_API_KEY environment variable
    )

    # Example with custom options
    stt_custom = STT(
        model_id="scribe_v1",
        language_code="eng",
        tag_audio_events=True,
        diarize=True,
        biased_keywords=["LiveKit", "ElevenLabs"],
        timestamps_granularity="word",
        num_speakers=2,
        api_key="your-api-key"
    )

    # Update options after initialization
    stt.update_options(
        diarize=True,
        num_speakers=2
    ) 