#!/usr/bin/env python3
"""
Main agent entry point for the participant service worker.
"""

import os
import logging
from dotenv import load_dotenv

from livekit.agents import JobContext, WorkerOptions, cli
from livekit.agents.llm import function_tool
from livekit.agents.voice import Agent, AgentSession
from livekit.plugins import silero, openai

from utils.logger import logger
from config import get_config

# Load environment variables and configuration
load_dotenv()
config = get_config()


class ParticipantServiceAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="You are a helpful assistant that can answer questions about participant services.",
        )

    @function_tool()
    async def example_function(self):
        await self.agent.say("This is an example function.")
        logger.info("Example function called")


async def entrypoint(ctx: JobContext):
    logger.info("Starting participant service agent")
    await ctx.connect()
    

    session = AgentSession(
        stt=openai.STT(),
        llm=openai.LLM(),
        tts=openai.TTS(),
        vad=silero.VAD.load(),
    )

    await session.start(agent=ParticipantServiceAgent(), room=ctx.room)


if __name__ == "__main__":
    logger.info("Initializing worker")
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
