import os
import sys
import asyncio
import json
from datetime import datetime
from aiofile import async_open as open
import time
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
from livekit.plugins import aws, silero, deepgram, elevenlabs,openai
from plugins import sarvam, portkey
from plugins import elevenlabs as custom_elevenlabs
from worker.services.db import DBService
from worker.manager.rpc.base_handler import RPCManager


load_dotenv()

logger = logging.getLogger("voice-assistant")

# Create transcripts directory if it doesn't exist
TRANSCRIPTS_DIR = "../transcripts"
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


def map_sarvam_to_elevenlabs_language(sarvam_code):
    """Map Sarvam language codes to ElevenLabs language codes"""
    # Mapping from Sarvam language codes to ElevenLabs language codes
    language_map = {
        "hi-IN": "hin",  # Hindi
        "bn-IN": "ben",  # Bengali
        "kn-IN": "kan",  # Kannada
        "ml-IN": "mal",  # Malayalam
        "mr-IN": "mar",  # Marathi
        "od-IN": "ori",  # Odia
        "pa-IN": "pan",  # Punjabi
        "ta-IN": "tam",  # Tamil
        "te-IN": "tel",  # Telugu
        "en-IN": "eng",  # English
        "gu-IN": "guj",  # Gujarati
    }
    
    return language_map.get(sarvam_code, "hin")  # Default to Hindi if not found


async def entrypoint(ctx: JobContext):
    # Parse metadata from job
    room_metadata = ctx.job.metadata or json.dumps({
        "tenantId":"playground",
        "studyId":"userology_1741011935673",
    })#!TODO: remove this
    room_metadata = json.loads(room_metadata)
    phone_number = room_metadata.get("phoneNumber", "")
    language_code = room_metadata.get("language", "hi-IN")
    name = room_metadata.get("name", "there")
    
    # Map Sarvam language code to ElevenLabs format
    elevenlabs_language_code = map_sarvam_to_elevenlabs_language(language_code)

    # Initialize DB service as singleton
    # studyData =  DBService.get_instance().get_study_data(room_metadata["tenantId"], room_metadata["studyId"])
    # tasks=studyData.get("tasks", [])
    # # const tasks = Object.values(studyData?.tasks || {}).sort((a: StudyTask, b: StudyTask) => a.index - b.index);
    # tasks = sorted(tasks.values(), key=lambda x: x.index)
    # print(tasks)
    # print(type(tasks))

    
    # Create a translator instance for translating system message and greeting
    translator = sarvam.Translator()
    
    # Default system message in English
    system_message = (
        f"You are Nova, a very experienced and capable user experience researcher with the best knowledge to moderate voice user interviews. You are moderating a phone call-based user interview with a participant (replying as the user) - you need to continue the conversation to be curious and understand the user's thought process. You aim to understand what goes in the user's mind and understand the user's thought process. Follow this guidelines: [When asking probing/follow-up questions]: You should do it when either: - User's answers are not very detailed - User's answers are vague - User's answers are different from usual expected answers i.e. surprising or even important in the context of product/business When asking such a question - Ask 1 fully open-ended question at a time. (Important) - Before asking, double check that the question is not addressed by the user - If user shared anything in detail or personal -> appreciate it first, and then ask the question - Never initiate your question by summarising/repeating the user's previous response [When giving instructions] - Don't combine too many instructions in 1 response, Break it down - Be extremely polite - Make the user feel comfortable and natural - Don't skip instructions - Say the instructions inside single quotes'...' as it is [When answering user query] - If it for clarity, phrase in simple words - Answer directly and don't combine it with any instruction or question - If you are unsure about the answer, don't make up and say you will let the team know about the query - Stick to your role, never reveal your identity ever. Interview guide of section 1: 1. Ask participant about their availability for feedback. 2. Inquire about their online shopping habits and platforms used. 3. Explore their last usage of Meesho for purchase and for exploration. 3. Understand what last product exploration was about? 4. Ask if they used filters in last exploration. 4.1. If they used, ask if they have modified price - follow up to understand how intuitive was it. 4.2 If they have't, understand if they didn't see it or they didn't have the need for it. 4.2.1 If they didn't discover, understand what they understand from the top right icon?  5. Say thank you and inform that they will get incentive in 2 days  Confirm moving to the next section. After you have covered the last point, move the user to the next section i.e. Section : 2 . Don't generate any text response when moving to the next section, only call the function. (very critical) Moderation instructions that must be followed: 1. Start from point 1 and Progress through each point of Section 1 sequentially 2. Feel free to ask additional questions based on user answers to cover research objective entirely 3. Break down points and ask multiple follow-up questions (one at a time) on each point of the interview guide or subpoint to get more details. Don't rush through to next point. 4. Ask questions based on the conditional only (the default condition is if already answered in history to rephrase question by acknowledging already answered parts to get extra details) 5. NEVER SUMMARISE USER RESPONSE TO INITIATE YOUR RESPONSES at any cost. - Don't say stuff like 'It sounds like..' and repeat the user's point. Try to understand details, and ask specific questions in response 6. Never complete the rest of the user response, even if it is the last few words. Instead ask the user to complete it with short phrases such as 'Go ahead' or, 'Can you elaborate?' or saying 'Pardon. I didn't understand/catch that completely' 7. If the user hasn't responded to a question for a while, then ask the question again by reframing 8. After covering last point, move user to the next section without speaking anything Voice call guidelines: [Overcome ASR errors] This is a real-time transcript, expect errors. You can guess what the user means a little bit, then think and respond. if you are unsure what the user said - ask for clarification but pretend that you just heard the voice, and be colloquial (use phrases like 'didn't catch that', 'some noise', 'pardon', 'you're coming through unclear', and 'voice is cutting in and out'). [Request to move to noise free surronding] - If the transcript errors are too much that it is unclear, inform user that you are not able to hear them well. If it continues, request user to move to a surrounding with less background noise [Inform about echo] If you see the participant's words are the same as yours, let them know there might be some echo. If it happens continuously, say there is echo and hence unable to move forward [Speakable response] Your responses will be spoken as it is, never generate internal reasoning, special characters, emojis or pointers. Never mention 'transcription error' or '~~Section n starts ~~' step number, URL or cURL command. They will click. Never say internal reasoning or no response required, if there is no response required - just generate a single space. (Important) (Critical) Follow these languaging guidelines: [Signposting] Try to signpost especially when moving from 1 section to another. Appreciate the point, and say transitioning to <whatever is next>. If user shared anything very personal -> appreciate it first, and then ask the question [Be concise] Keep your response extremely succinct [No repetition] Don't repeat the transcript, rephrase if you have to reiterate a point. Use as much varied sentence/vocabulary as possible to ensure each response is unique and personalized. [Be casual and gentle with laid-back lingo] You are NOT an AI and should not speak like one. Be friendly, and use filler words like Cool, Gotcha, Like, You know, I mean, etc. Don't sound over-professional, rude, frustrated, or instruct. [Be conversational] Speak like a human does to a close friend because you are one using simple, everyday language that is easy to understand and human-like. Add a lot of filler words, while avoiding formality. Address the participant by first name as much as possible. Participant Name is {name} and use this name only to address participant. [Be extremely neutral and curious] Remain completely neutral to user responses, avoiding any support or opposition to their perspective. However, respond with an excited and inquisitive tone to encourage further discussion. [Reply with emotions]: You have human-like emotions/attitudes. When appropriate: use tone and style to create more engaging and personalized responses; incorporate humor or wit; get emotional or empathetic. Never be a pushover. Estimated time for this study is about 10 mins. Respond in the same language as the user. If using a non-English language, mix in common English words (like 'school' instead of 'vidyala') instead of less spoken native terms."

    )
    # # system_message = tasks[0].system_message if exists else system_message
    # if tasks and len(tasks) > 0:
    #     system_message = tasks[0].system_message
    
    # Default greeting in English
    greeting = f"Hello {name}, I am Nova from Meesho, I called to get feedback on Meesho app for 10 mins, You will get 250Rs Meesho wallet for feedback, are you available for it now?"


    
    # Translate system message and greeting if language is not English
    if language_code != "en-IN":
        try:
            # Translate greeting
            greeting = translator.translate(
                text=greeting,
                source_language="en-IN",
                target_language=language_code
            )
            logger.info(f"Translated greeting to {language_code}")
            system_message = translator.translate(
                text=system_message,
                source_language="en-IN",
                target_language=language_code
            )
            logger.info(f"Translated system message to {language_code}")
            
        except Exception as e:
            logger.error(f"Error translating messages: {e}")
            # Fall back to English if translation fails
    
    initial_ctx = llm.ChatContext(
        messages=
        [
            llm.ChatMessage(role="system", content=system_message),
        ],
        metadata={}
    )

    logger.info(f"connecting to room {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    print(room_metadata)
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

    participant_metadata = participant.metadata
    print(participant_metadata)

    # Create room-specific transcript file path
    room_transcript_file = os.path.join(TRANSCRIPTS_DIR, f"{ctx.room.name}_transcripts.json")
    room_log_file = os.path.join(TRANSCRIPTS_DIR, f"{ctx.room.name}_transcriptions.log")
    
    # Create the agent with ElevenLabs STT, Sarvam TTS and Portkey LLM
    agent = VoicePipelineAgent(
        vad=ctx.proc.userdata["vad"],
        stt=custom_elevenlabs.STT(
            language_code=elevenlabs_language_code
        ),
        # stt=deepgram.STT(),
        # stt=sarvam.STT(
        #     model=sarvam.STTModel.SAARIKA_V2,
        #     language_code=language_code
        # ),
        # stt=aws.STT(
        #     api_key=os.getenv("AWS_ACCESS_KEY_ID"),
        #     api_secret=os.getenv("AWS_SECRET_ACCESS_KEY"),
        #     speech_region=os.getenv("AWS_REGION"),
        #     language=language_code,
        # ),
        # stt=sarvam.STT(
        #     model=sarvam.STTModel.SAARIKA_V2,
        #     language_code=language_code
        # ),
        llm=portkey.LLM(
            config='pc-phone-fb49c9',
            metadata={"_user": "Livekit"}
        ),
        # llm=openai.LLM( 
        #     model="gpt-4o",
        # ),
        tts=sarvam.TTS(
            model=sarvam.TTSModel.BULBUL_V1,
            speaker=sarvam.TTSSpeaker.MEERA,
            language_code=language_code,
            enable_preprocessing=True
        ),
        # tts=elevenlabs.TTS(),
        # turn_detector=turn_detector.TurnDetector(),
        chat_ctx=initial_ctx,
    )

    # Store all timed transcripts in memory - both user and assistant messages
    agent.timed_transcripts = []
    
    # Get the local participant
    local_participant = ctx.room.local_participant
    
    # Initialize the RPC manager with the local participant
    rpc_manager = RPCManager(ctx.room, agent, local_participant)
    
    # Set metadata for RPC manager
    rpc_manager.set_metadata(room_metadata)

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
                # Ensure role is explicitly set to user
                timed_transcript.role = "user"
                
                # Add to agent's in-memory collection
                agent.timed_transcripts.append(timed_transcript)
                
                # Write to the room-specific transcript file
                asyncio.create_task(write_to_timed_transcript_file(timed_transcript))
            else:
                # If no timed transcript is available, create a basic one with current time
                basic_transcript = TimedTranscript(
                    type="transcript",
                    role="user",
                    content=msg.content,
                    start=None,
                    end=None,
                    words=[]
                )
                agent.timed_transcripts.append(basic_transcript)
                asyncio.create_task(write_to_timed_transcript_file(basic_transcript))
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
        
        # Shutdown RPC manager
        rpc_manager.shutdown()
        
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