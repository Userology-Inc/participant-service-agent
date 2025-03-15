import os
import sys
import asyncio
import json
from datetime import datetime
from aiofile import async_open as open
# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
from dotenv import load_dotenv
from livekit import rtc,api
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    llm,
    metrics,
    Word,
    TimedTranscript,
)
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import silero, deepgram, elevenlabs
from plugins import sarvam, portkey
from plugins import elevenlabs as custom_elevenlabs


load_dotenv()

logger = logging.getLogger("voice-assistant")

# Create transcripts directory if it doesn't exist
TRANSCRIPTS_DIR = "transcripts"
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    # Parse metadata from job
    metadata = ctx.job.metadata
    metadata = json.loads(metadata)
    phone_number = metadata.get("phoneNumber", "")
    language_code = metadata.get("language", "hi-IN")
    
    # Create a translator instance for translating system message and greeting
    translator = sarvam.Translator()
    
    # Default system message in English
    system_message = (
        "You are a voice assistant created by LiveKit. Your interface with users will be voice. "
        "You should use short and concise responses, and avoiding usage of unpronouncable punctuation."
    )
    
    # Default greeting in English
    greeting = "Hey, how can I help you today?"
    
    # Translate system message and greeting if language is not English
    if language_code != "en-IN":
        try:
            # Translate system message
            system_message = translator.translate(
                text=system_message,
                source_language="en-IN",
                target_language=language_code
            )
            logger.info(f"Translated system message to {language_code}")
            
            # Translate greeting
            greeting = translator.translate(
                text=greeting,
                source_language="en-IN",
                target_language=language_code
            )
            logger.info(f"Translated greeting to {language_code}")
        except Exception as e:
            logger.error(f"Error translating messages: {e}")
            # Fall back to English if translation fails
    
    # Create the initial context with the translated system message
    initial_ctx = llm.ChatContext().append(
        role="system",
        text=system_message
    )

    logger.info(f"connecting to room {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    print(metadata)
    print(phone_number)
    if phone_number != "":
        await ctx.api.sip.create_sip_participant(api.CreateSIPParticipantRequest(
            room_name=ctx.room.name,
            sip_trunk_id=os.getenv("LIVEKIT_TRUNK_ID"),
            sip_call_to=phone_number,
            participant_identity="phone_user",
        ))

    # wait for the first participant to connect
    participant = await ctx.wait_for_participant()
    logger.info(f"starting voice assistant for participant {participant.identity}")

    # Create room-specific transcript file path
    room_transcript_file = os.path.join(TRANSCRIPTS_DIR, f"{ctx.room.name}_transcripts.json")
    room_log_file = os.path.join(TRANSCRIPTS_DIR, f"{ctx.room.name}_transcriptions.log")
    
    # Create the agent with ElevenLabs STT, Sarvam TTS and Portkey LLM
    agent = VoicePipelineAgent(
        vad=ctx.proc.userdata["vad"],
        # stt=custom_elevenlabs.STT(),
        # stt=deepgram.STT(),
        stt=sarvam.STT(
            model=sarvam.STTModel.SAARIKA_V2,
            language_code=language_code
        ),
        llm=portkey.LLM(
            config='pc-modera-fc0ed1',
            metadata={"_user": "Livekit"}
        ),
        tts=sarvam.TTS(
            model=sarvam.TTSModel.BULBUL_V1,
            speaker=sarvam.TTSSpeaker.MEERA,
            language_code=language_code
        ),
        # tts=elevenlabs.TTS(),
        # turn_detector=turn_detector.TurnDetector(),
        chat_ctx=initial_ctx,
    )

    # Store all timed transcripts in memory - both user and assistant messages
    agent.timed_transcripts = []

    agent.start(ctx.room, participant)

    usage_collector = metrics.UsageCollector()

    @agent.on("metrics_collected")
    def _on_metrics_collected(mtrcs: metrics.AgentMetrics):
        metrics.log_metrics(mtrcs)
        usage_collector.collect(mtrcs)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: ${summary}")

    ctx.add_shutdown_callback(log_usage)

    # listen to incoming chat messages, only required if you'd like the agent to
    # answer incoming messages from Chat
    chat = rtc.ChatManager(ctx.room)

    async def answer_from_text(txt: str):
        chat_ctx = agent.chat_ctx.copy()
        chat_ctx.append(role="user", text=txt)
        stream = agent.llm.chat(chat_ctx=chat_ctx)
        await agent.say(stream)

    @chat.on("message_received")
    def on_chat_received(msg: rtc.ChatMessage):
        if msg.message:
            asyncio.create_task(answer_from_text(msg.message))

    log_queue = asyncio.Queue()

    # Function to add a transcript to the collection and write to file
    async def add_to_timed_transcript(role, content, start_time=None, end_time=None, words=None):
        try:
            # Create a TimedTranscript object
            timed_transcript = TimedTranscript(
                type="transcript",
                role=role,
                content=content,
                start=start_time or 0.0,
                end=end_time or 0.0,
                words=[Word(text=w["text"], start=w["start"], end=w["end"]) 
                      for w in words] if isinstance(words, list) else []
            )
            
            # Add to agent's in-memory collection
            agent.timed_transcripts.append(timed_transcript)
            
            # Write to the room-specific transcript file
            asyncio.create_task(write_to_timed_transcript_file(timed_transcript))
            
            return timed_transcript
        except Exception as e:
            logger.exception(f"Error creating timed transcript: {e}")
            return None

    @agent.on("user_speech_committed")
    def on_user_speech_committed(msg: llm.ChatMessage, timed_transcript=None):
        # convert string lists to strings, drop images
        if isinstance(msg.content, list):
            msg.content = "\n".join(
                "[image]" if isinstance(x, llm.ChatImage) else x for x in msg
            )
        log_queue.put_nowait(f"[{datetime.now()}] USER:\n{msg.content}\n\n")
        
        # Add user message to timed transcript
        try:
            if timed_transcript:
                # If we received a timed transcript, use it directly
                agent.timed_transcripts.append(timed_transcript)
                # Write to the room-specific transcript file
                asyncio.create_task(write_to_timed_transcript_file(timed_transcript))
            else:
                # If no timed transcript is available, create a basic one
                asyncio.create_task(add_to_timed_transcript("user", msg.content))
        except Exception as e:
            logger.exception(f"Error handling user timed transcript: {e}")

    @agent.on("agent_speech_committed")
    def on_agent_speech_committed(msg: llm.ChatMessage, timed_transcript=None):
        log_queue.put_nowait(f"[{datetime.now()}] AGENT:\n{msg.content}\n\n")
        
        # Log the timed transcript if available
        try:
            if timed_transcript:
                # The timed_transcript is already a TimedTranscript object, so we can use it directly
                # Ensure role is explicitly set to assistant
                timed_transcript.role = "assistant"
                
                # Add to agent's in-memory collection
                agent.timed_transcripts.append(timed_transcript)
                
                # Write to the room-specific transcript file
                asyncio.create_task(write_to_timed_transcript_file(timed_transcript))
            else:
                # If no timed transcript is available, create a basic one
                asyncio.create_task(add_to_timed_transcript("assistant", msg.content))
        except Exception as e:
            logger.exception(f"Error handling agent timed transcript: {e}")

    async def write_transcription():
        async with open(room_log_file, "w") as f:
            while True:
                msg = await log_queue.get()
                if msg is None:
                    break
                await f.write(msg)

    async def write_to_timed_transcript_file(timed_transcript):
        """Write to the room-specific transcript file."""
        try:
            # Convert TimedTranscript to a serializable dictionary
            transcript_dict = {
                "type": timed_transcript.type,
                "role": timed_transcript.role,
                "content": timed_transcript.content,
                "start": timed_transcript.start,
                "end": timed_transcript.end,
                "words": [
                    {"text": word.text, "start": word.start, "end": word.end}
                    for word in timed_transcript.words
                ]
            }
            
            # Always write to the room-specific file
            if not os.path.exists(room_transcript_file):
                # Create the file with the first transcript
                async with open(room_transcript_file, "w") as f:
                    await f.write(json.dumps([transcript_dict], indent=2))
                return
            
            try:
                # Read existing content, add new transcript, write back
                async with open(room_transcript_file, "r") as f:
                    content = await f.read()
                    if content.strip():
                        transcripts = json.loads(content)
                    else:
                        transcripts = []
                    
                    transcripts.append(transcript_dict)
                
                async with open(room_transcript_file, "w") as f:
                    await f.write(json.dumps(transcripts, indent=2))
            except json.JSONDecodeError:
                # If file is corrupted, start fresh
                logger.warning(f"Transcript file {room_transcript_file} was corrupted, starting fresh")
                async with open(room_transcript_file, "w") as f:
                    await f.write(json.dumps([transcript_dict], indent=2))
        except Exception as e:
            logger.exception(f"Error writing timed transcript to file: {e}")

    write_task = asyncio.create_task(write_transcription())

    async def finish_queue():
        log_queue.put_nowait(None)
        await write_task
        
        # Write final version of all timed transcripts to room-specific file
        try:
            if hasattr(agent, 'timed_transcripts') and agent.timed_transcripts:
                # Convert all TimedTranscript objects to serializable dictionaries
                serializable_transcripts = []
                for tt in agent.timed_transcripts:
                    try:
                        transcript_dict = {
                            "type": tt.type,
                            "role": tt.role,
                            "content": tt.content,
                            "start": tt.start,
                            "end": tt.end,
                            "words": [
                                {"text": word.text, "start": word.start, "end": word.end}
                                for word in tt.words
                            ]
                        }
                        serializable_transcripts.append(transcript_dict)
                    except Exception as e:
                        logger.exception(f"Error serializing transcript: {e}")
                
                async with open(room_transcript_file, "w") as f:
                    await f.write(json.dumps(serializable_transcripts, indent=2))
        except Exception as e:
            logger.exception(f"Error writing final transcripts: {e}")

    ctx.add_shutdown_callback(finish_queue)

    # Use the translated greeting
    await agent.say(greeting, allow_interruptions=True)


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            agent_name="userology-ai"
        )
    )