import os
import sys

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
import logging
import json
import time
from datetime import datetime

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    llm,
    metrics,
)
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import silero, deepgram, elevenlabs
from plugins import sarvam, portkey
from plugins import elevenlabs as custom_elevenlabs

load_dotenv()

logger = logging.getLogger("voice-assistant")


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    initial_ctx = llm.ChatContext().append(
        role="system",
        text=(
            "You are a voice assistant created by LiveKit. Your interface with users will be voice. "
            "You should use short and concise responses, and avoiding usage of unpronouncable punctuation."
        ),
    )

    logger.info(f"connecting to room {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # wait for the first participant to connect
    participant = await ctx.wait_for_participant()
    logger.info(f"starting voice assistant for participant {participant.identity}")

    # Create the agent with ElevenLabs STT, Sarvam TTS and Portkey LLM
    agent = VoicePipelineAgent(
        vad=ctx.proc.userdata["vad"],
        stt=custom_elevenlabs.STT(),
        # stt=deepgram.STT(),
        llm=portkey.LLM(
            config='pc-modera-fc0ed1',
            metadata={"_user": "Livekit"}
        ),
        # tts=sarvam.TTS(
        #     model=sarvam.TTSModel.BULBUL_V1,
        #     speaker=sarvam.TTSSpeaker.MEERA,
        #     language_code=sarvam.LanguageCode.ENGLISH
        # ),
        tts=elevenlabs.TTS(),
        chat_ctx=initial_ctx,
    )

    usage_collector = metrics.UsageCollector()

    @agent.on("metrics_collected")
    def _on_metrics_collected(mtrcs: metrics.AgentMetrics):
        metrics.log_metrics(mtrcs)
        usage_collector.collect(mtrcs)
    
    # Add handlers for word timing events - with error handling
    @agent.on("user_speech_with_word_timings")
    def _on_user_speech_with_word_timings(word_timing_data):
        try:
            logger.info("User Speech with Word Timings:")
            
            # Check if word_timing_data is a list or a dictionary
            if isinstance(word_timing_data, list):
                # It's just a list of word timings
                logger.info("Words with timing:")
                for word in word_timing_data:
                    logger.info(f"  {word['text']}: start={word['start']:.3f}s, end={word['end']:.3f}s, confidence={word['confidence'] if 'confidence' in word else 1.0:.2f}")
            elif isinstance(word_timing_data, dict) and 'words' in word_timing_data:
                # It's a dictionary with text, start_time, end_time, and words
                if 'text' in word_timing_data:
                    logger.info(f"Text: {word_timing_data['text']}")
                if 'start_time' in word_timing_data:
                    logger.info(f"Start time: {word_timing_data['start_time']}")
                if 'end_time' in word_timing_data:
                    logger.info(f"End time: {word_timing_data['end_time']}")
                logger.info("Words with timing:")
                for word in word_timing_data['words']:
                    logger.info(f"  {word['text']}: start={word['start']:.3f}s, end={word['end']:.3f}s, confidence={word['confidence'] if 'confidence' in word else 1.0:.2f}")
            else:
                logger.warning(f"Unexpected word_timing_data format: {type(word_timing_data)}")
        except Exception as e:
            logger.error(f"Error in _on_user_speech_with_word_timings: {e}")
    
    @agent.on("agent_speech_with_word_timings")
    def _on_agent_speech_with_word_timings(word_timing_data):
        try:
            logger.info("Agent Speech with Word Timings:")
            
            # Check if word_timing_data is a list or a dictionary
            if isinstance(word_timing_data, list):
                # It's just a list of word timings
                logger.info("Words with timing:")
                for word in word_timing_data:
                    logger.info(f"  {word['text']}: start={word['start']:.3f}s, end={word['end']:.3f}s, confidence={word['confidence'] if 'confidence' in word else 1.0:.2f}")
            elif isinstance(word_timing_data, dict) and 'words' in word_timing_data:
                # It's a dictionary with text, start_time, end_time, and words
                if 'text' in word_timing_data:
                    logger.info(f"Text: {word_timing_data['text']}")
                if 'start_time' in word_timing_data:
                    logger.info(f"Start time: {word_timing_data['start_time']}")
                if 'end_time' in word_timing_data:
                    logger.info(f"End time: {word_timing_data['end_time']}")
                logger.info("Words with timing:")
                for word in word_timing_data['words']:
                    logger.info(f"  {word['text']}: start={word['start']:.3f}s, end={word['end']:.3f}s, confidence={word['confidence'] if 'confidence' in word else 1.0:.2f}")
            else:
                logger.warning(f"Unexpected word_timing_data format: {type(word_timing_data)}")
        except Exception as e:
            logger.error(f"Error in _on_agent_speech_with_word_timings: {e}")
    
    # Add handlers for speech committed events to print the chat context with timing information
    @agent.on("user_speech_committed")
    def _on_user_speech_committed(msg):
        try:
            print_timed_message(msg, "User")
        except Exception as e:
            logger.error(f"Error in _on_user_speech_committed: {e}")
    
    @agent.on("agent_speech_committed")
    def _on_agent_speech_committed(msg):
        try:
            print_timed_message(msg, "Agent")
        except Exception as e:
            logger.error(f"Error in _on_agent_speech_committed: {e}")
    
    def print_timed_message(msg, role):
        try:
            logger.info(f"\n{role} Message Committed to Chat Context:")
            logger.info(f"Text: {msg.content}")
            
            if hasattr(msg, 'word_timings') and msg.word_timings and hasattr(msg, 'start_time') and msg.start_time is not None and hasattr(msg, 'end_time') and msg.end_time is not None:
                logger.info(f"Speech duration: {msg.end_time - msg.start_time:.2f}s")
                logger.info(f"Timed Transcript:")
                
                # Format the timed transcript as JSON for better readability
                timed_transcript = {
                    "text": msg.content,
                    "start_time": msg.start_time,
                    "end_time": msg.end_time,
                    "words": [
                        {
                            "text": word["text"],
                            "start": word["start"],
                            "end": word["end"],
                            "confidence": word["confidence"] if "confidence" in word else 1.0
                        }
                        for word in msg.word_timings
                    ]
                }
                
                # Print the timed transcript as formatted JSON
                logger.info(f"timedTranscript: {json.dumps(timed_transcript, indent=2)}")
                
                # Save the timed transcript to a file
                save_timed_transcript_to_file(timed_transcript, role)
            else:
                logger.info("No timing information available for this message")
        except Exception as e:
            logger.error(f"Error in print_timed_message: {e}")
    
    def save_timed_transcript_to_file(timed_transcript, role):
        """Save the timed transcript to a JSON file"""
        try:
            # Validate the timed transcript
            if not isinstance(timed_transcript, dict) or 'text' not in timed_transcript:
                logger.warning("Invalid timed transcript format, skipping file save")
                return
                
            # Create a directory for timed transcripts if it doesn't exist
            os.makedirs("timed_transcripts", exist_ok=True)
            
            # Generate a filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"timed_transcripts/{role.lower()}_{timestamp}.json"
            
            # Write the timed transcript to the file
            with open(filename, 'w') as f:
                json.dump(timed_transcript, f, indent=2)
            
            logger.info(f"Saved timed transcript to {filename}")
        except Exception as e:
            logger.error(f"Error saving timed transcript to file: {e}")

    async def log_usage():
        try:
            summary = usage_collector.get_summary()
            logger.info(f"Usage: ${summary}")
            
            # Print the final chat context with timing information
            logger.info("\nFinal Chat Context with Timing Information:")
            
            # Create a complete transcript with all messages
            complete_transcript = {
                "conversation": [],
                "timestamp": datetime.now().isoformat(),
            }
            
            for i, msg in enumerate(agent.chat_ctx.messages):
                try:
                    role = "system" if msg.role == "system" else "user" if msg.role == "user" else "assistant"
                    logger.info(f"[{i}] {role.capitalize()}: {msg.content}")
                    
                    message_data = {
                        "role": role,
                        "content": msg.content,
                        "index": i
                    }
                    
                    if hasattr(msg, 'word_timings') and msg.word_timings and hasattr(msg, 'start_time') and msg.start_time is not None and hasattr(msg, 'end_time') and msg.end_time is not None:
                        logger.info(f"  Speech duration: {msg.end_time - msg.start_time:.2f}s")
                        logger.info(f"  Word count: {len(msg.word_timings)}")
                        logger.info(f"  First few words with timing:")
                        
                        # Print the first 3 words with timing (or all if less than 3)
                        for word in msg.word_timings[:3]:
                            logger.info(f"    {word['text']}: start={word['start']:.3f}s, end={word['end']:.3f}s")
                        
                        if len(msg.word_timings) > 3:
                            logger.info(f"    ... and {len(msg.word_timings) - 3} more words")
                        
                        # Add timing information to the message data
                        message_data["start_time"] = msg.start_time
                        message_data["end_time"] = msg.end_time
                        message_data["word_timings"] = msg.word_timings
                    
                    complete_transcript["conversation"].append(message_data)
                except Exception as e:
                    logger.error(f"Error processing message {i}: {e}")
            
            # Save the complete transcript to a file
            try:
                os.makedirs("timed_transcripts", exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"timed_transcripts/complete_conversation_{timestamp}.json"
                
                with open(filename, 'w') as f:
                    json.dump(complete_transcript, f, indent=2)
                
                logger.info(f"Saved complete conversation transcript to {filename}")
                
                # Create HTML visualization
                create_html_visualization(complete_transcript, timestamp)
            except Exception as e:
                logger.error(f"Error saving complete transcript to file: {e}")
        except Exception as e:
            logger.error(f"Error in log_usage: {e}")

    def create_html_visualization(transcript, timestamp):
        """Create a simple HTML visualization of the timed transcript"""
        try:
            # Validate the transcript
            if not isinstance(transcript, dict) or 'conversation' not in transcript:
                logger.warning("Invalid transcript format, skipping HTML visualization")
                return
                
            # Check if there are any messages with timing information
            has_timing_info = False
            for msg in transcript["conversation"]:
                if "start_time" in msg and "end_time" in msg and "word_timings" in msg:
                    has_timing_info = True
                    break
                    
            if not has_timing_info:
                logger.warning("No timing information found in transcript, skipping HTML visualization")
                return
            
            html_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Timed Transcript Visualization</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    .message { margin-bottom: 20px; padding: 10px; border-radius: 5px; }
                    .system { background-color: #f0f0f0; }
                    .user { background-color: #e1f5fe; }
                    .assistant { background-color: #e8f5e9; }
                    .word { display: inline-block; margin-right: 5px; padding: 2px; }
                    .word-timing { font-size: 10px; color: #666; display: block; }
                    .message-header { font-weight: bold; margin-bottom: 5px; }
                    .message-content { margin-bottom: 10px; }
                    .timing-info { font-size: 12px; color: #666; margin-bottom: 10px; }
                    .word-container { margin-top: 10px; }
                    
                    /* Timeline styles */
                    .timeline-container { 
                        margin-top: 20px; 
                        border: 1px solid #ccc; 
                        padding: 10px; 
                        position: relative;
                        height: 150px;
                    }
                    .timeline-scale {
                        position: absolute;
                        bottom: 0;
                        left: 0;
                        right: 0;
                        height: 20px;
                        border-top: 1px solid #ccc;
                    }
                    .timeline-marker {
                        position: absolute;
                        bottom: 0;
                        height: 10px;
                        border-left: 1px solid #999;
                        font-size: 10px;
                    }
                    .timeline-word {
                        position: absolute;
                        height: 20px;
                        background-color: rgba(0,0,0,0.1);
                        border-radius: 3px;
                        font-size: 10px;
                        padding: 2px;
                        overflow: hidden;
                        white-space: nowrap;
                    }
                    .timeline-word.user { background-color: rgba(33, 150, 243, 0.3); }
                    .timeline-word.assistant { background-color: rgba(76, 175, 80, 0.3); }
                    .timeline-segment {
                        position: absolute;
                        height: 30px;
                        border-radius: 3px;
                        font-size: 12px;
                        padding: 5px;
                        overflow: hidden;
                        white-space: nowrap;
                    }
                    .timeline-segment.user { 
                        background-color: rgba(33, 150, 243, 0.2); 
                        border: 1px solid rgba(33, 150, 243, 0.5);
                    }
                    .timeline-segment.assistant { 
                        background-color: rgba(76, 175, 80, 0.2); 
                        border: 1px solid rgba(76, 175, 80, 0.5);
                    }
                    .tabs {
                        display: flex;
                        margin-bottom: 10px;
                    }
                    .tab {
                        padding: 10px 20px;
                        cursor: pointer;
                        border: 1px solid #ccc;
                        border-bottom: none;
                        border-radius: 5px 5px 0 0;
                        margin-right: 5px;
                    }
                    .tab.active {
                        background-color: #f0f0f0;
                        font-weight: bold;
                    }
                    .tab-content {
                        display: none;
                        border: 1px solid #ccc;
                        padding: 20px;
                    }
                    .tab-content.active {
                        display: block;
                    }
                </style>
            </head>
            <body>
                <h1>Timed Transcript Visualization</h1>
                <p>Timestamp: {timestamp}</p>
                
                <div class="tabs">
                    <div class="tab active" onclick="showTab('conversation')">Conversation</div>
                    <div class="tab" onclick="showTab('timeline')">Timeline</div>
                </div>
                
                <div id="conversation" class="tab-content active">
            """
            
            # Add conversation content
            for msg in transcript["conversation"]:
                role = msg["role"]
                content = msg["content"]
                
                html_content += f"""
                <div class="message {role}">
                    <div class="message-header">{role.capitalize()}</div>
                    <div class="message-content">{content}</div>
                """
                
                if "word_timings" in msg and "start_time" in msg and "end_time" in msg:
                    duration = msg["end_time"] - msg["start_time"]
                    html_content += f"""
                    <div class="timing-info">
                        Start: {msg["start_time"]:.2f}s, End: {msg["end_time"]:.2f}s, Duration: {duration:.2f}s
                    </div>
                    <div class="word-container">
                    """
                    
                    for word in msg["word_timings"]:
                        word_duration = word["end"] - word["start"]
                        html_content += f"""
                        <div class="word">
                            {word["text"]}
                            <span class="word-timing">
                                {word["start"]:.2f}s - {word["end"]:.2f}s ({word_duration:.2f}s)
                            </span>
                        </div>
                        """
                    
                    html_content += "</div>"
                
                html_content += "</div>"
            
            html_content += """
                </div>
                
                <div id="timeline" class="tab-content">
                    <h2>Timeline View</h2>
                    <p>This timeline shows when each word was spoken during the conversation.</p>
            """
            
            # Calculate the total duration of the conversation
            start_times = []
            end_times = []
            
            for msg in transcript["conversation"]:
                if "start_time" in msg and "end_time" in msg:
                    start_times.append(msg["start_time"])
                    end_times.append(msg["end_time"])
            
            if start_times and end_times:
                min_time = min(start_times)
                max_time = max(end_times)
                total_duration = max_time - min_time
                
                # Add 10% padding
                padding = total_duration * 0.1
                min_time = max(0, min_time - padding)
                max_time = max_time + padding
                total_duration = max_time - min_time
                
                # Create the timeline container
                html_content += f"""
                    <div class="timeline-container">
                """
                
                # Add message segments to the timeline
                for i, msg in enumerate(transcript["conversation"]):
                    if "start_time" in msg and "end_time" in msg and msg["role"] in ["user", "assistant"]:
                        role = msg["role"]
                        start_pos = ((msg["start_time"] - min_time) / total_duration) * 100
                        width = ((msg["end_time"] - msg["start_time"]) / total_duration) * 100
                        
                        # Position segments at different heights based on role
                        top = 10 if role == "user" else 50
                        
                        html_content += f"""
                        <div class="timeline-segment {role}" 
                             style="left: {start_pos}%; width: {width}%; top: {top}px;" 
                             title="{role.capitalize()}: {msg['start_time']:.2f}s - {msg['end_time']:.2f}s">
                            {role.capitalize()}
                        </div>
                        """
                        
                        # Add individual words to the timeline
                        if "word_timings" in msg:
                            for word in msg["word_timings"]:
                                word_start_pos = ((word["start"] + msg["start_time"] - min_time) / total_duration) * 100
                                word_width = ((word["end"] - word["start"]) / total_duration) * 100
                                
                                # Position words at different heights based on role
                                word_top = 35 if role == "user" else 75
                                
                                html_content += f"""
                                <div class="timeline-word {role}" 
                                     style="left: {word_start_pos}%; width: {word_width}%; top: {word_top}px;" 
                                     title="{word['text']}: {word['start']:.2f}s - {word['end']:.2f}s">
                                    {word['text']}
                                </div>
                                """
                
                # Add time scale markers
                num_markers = 10
                for i in range(num_markers + 1):
                    marker_time = min_time + (total_duration * i / num_markers)
                    marker_pos = (i / num_markers) * 100
                    
                    html_content += f"""
                    <div class="timeline-marker" style="left: {marker_pos}%;">
                        {marker_time:.1f}s
                    </div>
                    """
                
                html_content += """
                    <div class="timeline-scale"></div>
                    </div>
                """
            else:
                html_content += "<p>No timing data available for timeline visualization.</p>"
            
            html_content += """
                </div>
                
                <script>
                function showTab(tabId) {
                    // Hide all tab contents
                    var tabContents = document.getElementsByClassName('tab-content');
                    for (var i = 0; i < tabContents.length; i++) {
                        tabContents[i].classList.remove('active');
                    }
                    
                    // Deactivate all tabs
                    var tabs = document.getElementsByClassName('tab');
                    for (var i = 0; i < tabs.length; i++) {
                        tabs[i].classList.remove('active');
                    }
                    
                    // Activate the selected tab and content
                    document.getElementById(tabId).classList.add('active');
                    var selectedTab = document.querySelector('.tab[onclick="showTab(\\'' + tabId + '\\')"]');
                    if (selectedTab) {
                        selectedTab.classList.add('active');
                    }
                }
                </script>
            </body>
            </html>
            """
            
            html_filename = f"timed_transcripts/visualization_{timestamp}.html"
            with open(html_filename, 'w') as f:
                f.write(html_content.format(timestamp=transcript["timestamp"]))
            
            logger.info(f"Created HTML visualization at {html_filename}")
        except Exception as e:
            logger.error(f"Error creating HTML visualization: {e}")

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

    # Now start the agent after all event handlers are registered
    agent.start(ctx.room, participant)
    
    # Say the welcome message after starting the agent
import os
import sys

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
import logging
import json
import time
from datetime import datetime

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    llm,
    metrics,
)
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import silero, deepgram, elevenlabs
from plugins import sarvam, portkey
from plugins import elevenlabs as custom_elevenlabs

load_dotenv()

logger = logging.getLogger("voice-assistant")


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    initial_ctx = llm.ChatContext().append(
        role="system",
        text=(
            "You are a voice assistant created by LiveKit. Your interface with users will be voice. "
            "You should use short and concise responses, and avoiding usage of unpronouncable punctuation."
        ),
    )

    logger.info(f"connecting to room {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # wait for the first participant to connect
    participant = await ctx.wait_for_participant()
    logger.info(f"starting voice assistant for participant {participant.identity}")

    # Create the agent with ElevenLabs STT, Sarvam TTS and Portkey LLM
    agent = VoicePipelineAgent(
        vad=ctx.proc.userdata["vad"],
        stt=custom_elevenlabs.STT(),
        # stt=deepgram.STT(),
        llm=portkey.LLM(
            config='pc-modera-fc0ed1',
            metadata={"_user": "Livekit"}
        ),
        # tts=sarvam.TTS(
        #     model=sarvam.TTSModel.BULBUL_V1,
        #     speaker=sarvam.TTSSpeaker.MEERA,
        #     language_code=sarvam.LanguageCode.ENGLISH
        # ),
        tts=elevenlabs.TTS(),
        chat_ctx=initial_ctx,
    )

    usage_collector = metrics.UsageCollector()

    @agent.on("metrics_collected")
    def _on_metrics_collected(mtrcs: metrics.AgentMetrics):
        metrics.log_metrics(mtrcs)
        usage_collector.collect(mtrcs)
    
    # Add handlers for word timing events - with error handling
    @agent.on("user_speech_with_word_timings")
    def _on_user_speech_with_word_timings(word_timing_data):
        try:
            logger.info("User Speech with Word Timings:")
            
            # Check if word_timing_data is a list or a dictionary
            if isinstance(word_timing_data, list):
                # It's just a list of word timings
                logger.info("Words with timing:")
                for word in word_timing_data:
                    logger.info(f"  {word['text']}: start={word['start']:.3f}s, end={word['end']:.3f}s, confidence={word['confidence'] if 'confidence' in word else 1.0:.2f}")
            elif isinstance(word_timing_data, dict) and 'words' in word_timing_data:
                # It's a dictionary with text, start_time, end_time, and words
                if 'text' in word_timing_data:
                    logger.info(f"Text: {word_timing_data['text']}")
                if 'start_time' in word_timing_data:
                    logger.info(f"Start time: {word_timing_data['start_time']}")
                if 'end_time' in word_timing_data:
                    logger.info(f"End time: {word_timing_data['end_time']}")
                logger.info("Words with timing:")
                for word in word_timing_data['words']:
                    logger.info(f"  {word['text']}: start={word['start']:.3f}s, end={word['end']:.3f}s, confidence={word['confidence'] if 'confidence' in word else 1.0:.2f}")
            else:
                logger.warning(f"Unexpected word_timing_data format: {type(word_timing_data)}")
        except Exception as e:
            logger.error(f"Error in _on_user_speech_with_word_timings: {e}")
    
    @agent.on("agent_speech_with_word_timings")
    def _on_agent_speech_with_word_timings(word_timing_data):
        try:
            logger.info("Agent Speech with Word Timings:")
            
            # Check if word_timing_data is a list or a dictionary
            if isinstance(word_timing_data, list):
                # It's just a list of word timings
                logger.info("Words with timing:")
                for word in word_timing_data:
                    logger.info(f"  {word['text']}: start={word['start']:.3f}s, end={word['end']:.3f}s, confidence={word['confidence'] if 'confidence' in word else 1.0:.2f}")
            elif isinstance(word_timing_data, dict) and 'words' in word_timing_data:
                # It's a dictionary with text, start_time, end_time, and words
                if 'text' in word_timing_data:
                    logger.info(f"Text: {word_timing_data['text']}")
                if 'start_time' in word_timing_data:
                    logger.info(f"Start time: {word_timing_data['start_time']}")
                if 'end_time' in word_timing_data:
                    logger.info(f"End time: {word_timing_data['end_time']}")
                logger.info("Words with timing:")
                for word in word_timing_data['words']:
                    logger.info(f"  {word['text']}: start={word['start']:.3f}s, end={word['end']:.3f}s, confidence={word['confidence'] if 'confidence' in word else 1.0:.2f}")
            else:
                logger.warning(f"Unexpected word_timing_data format: {type(word_timing_data)}")
        except Exception as e:
            logger.error(f"Error in _on_agent_speech_with_word_timings: {e}")
    
    # Add handlers for speech committed events to print the chat context with timing information
    @agent.on("user_speech_committed")
    def _on_user_speech_committed(msg):
        try:
            print_timed_message(msg, "User")
        except Exception as e:
            logger.error(f"Error in _on_user_speech_committed: {e}")
    
    @agent.on("agent_speech_committed")
    def _on_agent_speech_committed(msg):
        try:
            print_timed_message(msg, "Agent")
        except Exception as e:
            logger.error(f"Error in _on_agent_speech_committed: {e}")
    
    def print_timed_message(msg, role):
        try:
            logger.info(f"\n{role} Message Committed to Chat Context:")
            logger.info(f"Text: {msg.content}")
            
            if hasattr(msg, 'word_timings') and msg.word_timings and hasattr(msg, 'start_time') and msg.start_time is not None and hasattr(msg, 'end_time') and msg.end_time is not None:
                logger.info(f"Speech duration: {msg.end_time - msg.start_time:.2f}s")
                logger.info(f"Timed Transcript:")
                
                # Format the timed transcript as JSON for better readability
                timed_transcript = {
                    "text": msg.content,
                    "start_time": msg.start_time,
                    "end_time": msg.end_time,
                    "words": [
                        {
                            "text": word["text"],
                            "start": word["start"],
                            "end": word["end"],
                            "confidence": word["confidence"] if "confidence" in word else 1.0
                        }
                        for word in msg.word_timings
                    ]
                }
                
                # Print the timed transcript as formatted JSON
                logger.info(f"timedTranscript: {json.dumps(timed_transcript, indent=2)}")
                
                # Save the timed transcript to a file
                save_timed_transcript_to_file(timed_transcript, role)
            else:
                logger.info("No timing information available for this message")
        except Exception as e:
            logger.error(f"Error in print_timed_message: {e}")
    
    def save_timed_transcript_to_file(timed_transcript, role):
        """Save the timed transcript to a JSON file"""
        try:
            # Validate the timed transcript
            if not isinstance(timed_transcript, dict) or 'text' not in timed_transcript:
                logger.warning("Invalid timed transcript format, skipping file save")
                return
                
            # Create a directory for timed transcripts if it doesn't exist
            os.makedirs("timed_transcripts", exist_ok=True)
            
            # Generate a filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"timed_transcripts/{role.lower()}_{timestamp}.json"
            
            # Write the timed transcript to the file
            with open(filename, 'w') as f:
                json.dump(timed_transcript, f, indent=2)
            
            logger.info(f"Saved timed transcript to {filename}")
        except Exception as e:
            logger.error(f"Error saving timed transcript to file: {e}")

    async def log_usage():
        try:
            summary = usage_collector.get_summary()
            logger.info(f"Usage: ${summary}")
            
            # Print the final chat context with timing information
            logger.info("\nFinal Chat Context with Timing Information:")
            
            # Create a complete transcript with all messages
            complete_transcript = {
                "conversation": [],
                "timestamp": datetime.now().isoformat(),
            }
            
            for i, msg in enumerate(agent.chat_ctx.messages):
                try:
                    role = "system" if msg.role == "system" else "user" if msg.role == "user" else "assistant"
                    logger.info(f"[{i}] {role.capitalize()}: {msg.content}")
                    
                    message_data = {
                        "role": role,
                        "content": msg.content,
                        "index": i
                    }
                    
                    if msg.word_timings and msg.start_time is not None and msg.end_time is not None:
                        logger.info(f"  Speech duration: {msg.end_time - msg.start_time:.2f}s")
                        logger.info(f"  Word count: {len(msg.word_timings)}")
                        logger.info(f"  First few words with timing:")
                        
                        # Print the first 3 words with timing (or all if less than 3)
                        for word in msg.word_timings[:3]:
                            logger.info(f"    {word['text']}: start={word['start']:.3f}s, end={word['end']:.3f}s")
                        
                        if len(msg.word_timings) > 3:
                            logger.info(f"    ... and {len(msg.word_timings) - 3} more words")
                        
                        # Add timing information to the message data
                        message_data["start_time"] = msg.start_time
                        message_data["end_time"] = msg.end_time
                        message_data["word_timings"] = msg.word_timings
                    
                    complete_transcript["conversation"].append(message_data)
                except Exception as e:
                    logger.error(f"Error processing message {i}: {e}")
            
            # Save the complete transcript to a file
            try:
                os.makedirs("timed_transcripts", exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"timed_transcripts/complete_conversation_{timestamp}.json"
                
                with open(filename, 'w') as f:
                    json.dump(complete_transcript, f, indent=2)
                
                logger.info(f"Saved complete conversation transcript to {filename}")
                
                # Create HTML visualization
                create_html_visualization(complete_transcript, timestamp)
            except Exception as e:
                logger.error(f"Error saving complete transcript to file: {e}")
        except Exception as e:
            logger.error(f"Error in log_usage: {e}")

    def create_html_visualization(transcript, timestamp):
        """Create a simple HTML visualization of the timed transcript"""
        try:
            # Validate the transcript
            if not isinstance(transcript, dict) or 'conversation' not in transcript:
                logger.warning("Invalid transcript format, skipping HTML visualization")
                return
                
            # Check if there are any messages with timing information
            has_timing_info = False
            for msg in transcript["conversation"]:
                if "start_time" in msg and "end_time" in msg and "word_timings" in msg:
                    has_timing_info = True
                    break
                    
            if not has_timing_info:
                logger.warning("No timing information found in transcript, skipping HTML visualization")
                return
            
            html_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Timed Transcript Visualization</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    .message { margin-bottom: 20px; padding: 10px; border-radius: 5px; }
                    .system { background-color: #f0f0f0; }
                    .user { background-color: #e1f5fe; }
                    .assistant { background-color: #e8f5e9; }
                    .word { display: inline-block; margin-right: 5px; padding: 2px; }
                    .word-timing { font-size: 10px; color: #666; display: block; }
                    .message-header { font-weight: bold; margin-bottom: 5px; }
                    .message-content { margin-bottom: 10px; }
                    .timing-info { font-size: 12px; color: #666; margin-bottom: 10px; }
                    .word-container { margin-top: 10px; }
                    
                    /* Timeline styles */
                    .timeline-container { 
                        margin-top: 20px; 
                        border: 1px solid #ccc; 
                        padding: 10px; 
                        position: relative;
                        height: 150px;
                    }
                    .timeline-scale {
                        position: absolute;
                        bottom: 0;
                        left: 0;
                        right: 0;
                        height: 20px;
                        border-top: 1px solid #ccc;
                    }
                    .timeline-marker {
                        position: absolute;
                        bottom: 0;
                        height: 10px;
                        border-left: 1px solid #999;
                        font-size: 10px;
                    }
                    .timeline-word {
                        position: absolute;
                        height: 20px;
                        background-color: rgba(0,0,0,0.1);
                        border-radius: 3px;
                        font-size: 10px;
                        padding: 2px;
                        overflow: hidden;
                        white-space: nowrap;
                    }
                    .timeline-word.user { background-color: rgba(33, 150, 243, 0.3); }
                    .timeline-word.assistant { background-color: rgba(76, 175, 80, 0.3); }
                    .timeline-segment {
                        position: absolute;
                        height: 30px;
                        border-radius: 3px;
                        font-size: 12px;
                        padding: 5px;
                        overflow: hidden;
                        white-space: nowrap;
                    }
                    .timeline-segment.user { 
                        background-color: rgba(33, 150, 243, 0.2); 
                        border: 1px solid rgba(33, 150, 243, 0.5);
                    }
                    .timeline-segment.assistant { 
                        background-color: rgba(76, 175, 80, 0.2); 
                        border: 1px solid rgba(76, 175, 80, 0.5);
                    }
                    .tabs {
                        display: flex;
                        margin-bottom: 10px;
                    }
                    .tab {
                        padding: 10px 20px;
                        cursor: pointer;
                        border: 1px solid #ccc;
                        border-bottom: none;
                        border-radius: 5px 5px 0 0;
                        margin-right: 5px;
                    }
                    .tab.active {
                        background-color: #f0f0f0;
                        font-weight: bold;
                    }
                    .tab-content {
                        display: none;
                        border: 1px solid #ccc;
                        padding: 20px;
                    }
                    .tab-content.active {
                        display: block;
                    }
                </style>
            </head>
            <body>
                <h1>Timed Transcript Visualization</h1>
                <p>Timestamp: {timestamp}</p>
                
                <div class="tabs">
                    <div class="tab active" onclick="showTab('conversation')">Conversation</div>
                    <div class="tab" onclick="showTab('timeline')">Timeline</div>
                </div>
                
                <div id="conversation" class="tab-content active">
            """
            
            # Add conversation content
            for msg in transcript["conversation"]:
                role = msg["role"]
                content = msg["content"]
                
                html_content += f"""
                <div class="message {role}">
                    <div class="message-header">{role.capitalize()}</div>
                    <div class="message-content">{content}</div>
                """
                
                if "word_timings" in msg and "start_time" in msg and "end_time" in msg:
                    duration = msg["end_time"] - msg["start_time"]
                    html_content += f"""
                    <div class="timing-info">
                        Start: {msg["start_time"]:.2f}s, End: {msg["end_time"]:.2f}s, Duration: {duration:.2f}s
                    </div>
                    <div class="word-container">
                    """
                    
                    for word in msg["word_timings"]:
                        word_duration = word["end"] - word["start"]
                        html_content += f"""
                        <div class="word">
                            {word["text"]}
                            <span class="word-timing">
                                {word["start"]:.2f}s - {word["end"]:.2f}s ({word_duration:.2f}s)
                            </span>
                        </div>
                        """
                    
                    html_content += "</div>"
                
                html_content += "</div>"
            
            html_content += """
                </div>
                
                <div id="timeline" class="tab-content">
                    <h2>Timeline View</h2>
                    <p>This timeline shows when each word was spoken during the conversation.</p>
            """
            
            # Calculate the total duration of the conversation
            start_times = []
            end_times = []
            
            for msg in transcript["conversation"]:
                if "start_time" in msg and "end_time" in msg:
                    start_times.append(msg["start_time"])
                    end_times.append(msg["end_time"])
            
            if start_times and end_times:
                min_time = min(start_times)
                max_time = max(end_times)
                total_duration = max_time - min_time
                
                # Add 10% padding
                padding = total_duration * 0.1
                min_time = max(0, min_time - padding)
                max_time = max_time + padding
                total_duration = max_time - min_time
                
                # Create the timeline container
                html_content += f"""
                    <div class="timeline-container">
                """
                
                # Add message segments to the timeline
                for i, msg in enumerate(transcript["conversation"]):
                    if "start_time" in msg and "end_time" in msg and msg["role"] in ["user", "assistant"]:
                        role = msg["role"]
                        start_pos = ((msg["start_time"] - min_time) / total_duration) * 100
                        width = ((msg["end_time"] - msg["start_time"]) / total_duration) * 100
                        
                        # Position segments at different heights based on role
                        top = 10 if role == "user" else 50
                        
                        html_content += f"""
                        <div class="timeline-segment {role}" 
                             style="left: {start_pos}%; width: {width}%; top: {top}px;" 
                             title="{role.capitalize()}: {msg['start_time']:.2f}s - {msg['end_time']:.2f}s">
                            {role.capitalize()}
                        </div>
                        """
                        
                        # Add individual words to the timeline
                        if "word_timings" in msg:
                            for word in msg["word_timings"]:
                                word_start_pos = ((word["start"] + msg["start_time"] - min_time) / total_duration) * 100
                                word_width = ((word["end"] - word["start"]) / total_duration) * 100
                                
                                # Position words at different heights based on role
                                word_top = 35 if role == "user" else 75
                                
                                html_content += f"""
                                <div class="timeline-word {role}" 
                                     style="left: {word_start_pos}%; width: {word_width}%; top: {word_top}px;" 
                                     title="{word['text']}: {word['start']:.2f}s - {word['end']:.2f}s">
                                    {word['text']}
                                </div>
                                """
                
                # Add time scale markers
                num_markers = 10
                for i in range(num_markers + 1):
                    marker_time = min_time + (total_duration * i / num_markers)
                    marker_pos = (i / num_markers) * 100
                    
                    html_content += f"""
                    <div class="timeline-marker" style="left: {marker_pos}%;">
                        {marker_time:.1f}s
                    </div>
                    """
                
                html_content += """
                    <div class="timeline-scale"></div>
                    </div>
                """
            else:
                html_content += "<p>No timing data available for timeline visualization.</p>"
            
            html_content += """
                </div>
                
                <script>
                function showTab(tabId) {
                    // Hide all tab contents
                    var tabContents = document.getElementsByClassName('tab-content');
                    for (var i = 0; i < tabContents.length; i++) {
                        tabContents[i].classList.remove('active');
                    }
                    
                    // Deactivate all tabs
                    var tabs = document.getElementsByClassName('tab');
                    for (var i = 0; i < tabs.length; i++) {
                        tabs[i].classList.remove('active');
                    }
                    
                    // Activate the selected tab and content
                    document.getElementById(tabId).classList.add('active');
                    var selectedTab = document.querySelector('.tab[onclick="showTab(\\'' + tabId + '\\')"]');
                    if (selectedTab) {
                        selectedTab.classList.add('active');
                    }
                }
                </script>
            </body>
            </html>
            """
            
            html_filename = f"timed_transcripts/visualization_{timestamp}.html"
            with open(html_filename, 'w') as f:
                f.write(html_content.format(timestamp=transcript["timestamp"]))
            
            logger.info(f"Created HTML visualization at {html_filename}")
        except Exception as e:
            logger.error(f"Error creating HTML visualization: {e}")

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

    # Now start the agent after all event handlers are registered
    agent.start(ctx.room, participant)
    
    # Say the welcome message after starting the agent
    await agent.say("Hey, how can I help you today?", allow_interruptions=True)


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        ),
    )
