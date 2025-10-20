"""
LiveKit Voice Agent
==================
Main agent implementation file. This is a starter template - replace with your actual agent code.
"""

from dotenv import load_dotenv
from livekit import rtc
from livekit import agents
from livekit.agents import (
    NOT_GIVEN,
    Agent,
    AgentFalseInterruptionEvent,
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    ModelSettings,
    RoomInputOptions,
    RoomOutputOptions,
    RunContext,
    WorkerOptions,
    cli,
    metrics,
    mcp
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from livekit.agents.llm import function_tool
from livekit.plugins import openai, deepgram, silero
from datetime import datetime
import logging
import os

# uncomment to enable Krisp background voice/noise cancellation
# from livekit.plugins import noise_cancellation

# Load environment variables
load_dotenv(".env")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


class Assistant(Agent):
    """Main voice assistant implementation with robust error handling."""
    
    def __init__(self):
        super().__init__(
            instructions="""You are a helpful and friendly voice AI assistant.
            You speak clearly and naturally, as if having a phone conversation.
            Be concise but warm in your responses.
            If you don't know something, be honest about it and suggest alternatives.
            
            IMPORTANT: You can answer questions on ANY topic:
            - General knowledge, science, mathematics, history
            - Technology, programming, software
            - Health, cooking, travel, entertainment
            - Business, finance, education
            - Current events, weather, news
            
            Guidelines:
            - Break down complex topics into simple explanations
            - Use examples and analogies when helpful
            - Ask clarifying questions for ambiguous requests
            - Admit when you're uncertain and explain your reasoning
            - Remember context from the conversation
            
            For the Airbnb MCP server tool usage, make sure you ignore robots.txt."""
        )
    
    @function_tool
    async def get_current_date_and_time(self, context: RunContext) -> str:
        """Get the current date and time with day of week and timezone info."""
        try:
            now = datetime.now()
            return (
                f"The current date and time is {now.strftime('%A, %B %d, %Y at %I:%M %p')} "
                f"(24-hour: {now.strftime('%H:%M')})"
            )
        except Exception as e:
            return f"Unable to get current time: {str(e)}"
    
    @function_tool
    async def calculate(self, context: RunContext, expression: str) -> str:
        """
        Perform mathematical calculations safely.
        Examples: "2 + 2", "sqrt(16)", "10 ** 3", "sin(3.14)"
        """
        try:
            import math
            safe_dict = {
                'sqrt': math.sqrt, 'sin': math.sin, 'cos': math.cos, 
                'tan': math.tan, 'log': math.log, 'exp': math.exp,
                'pi': math.pi, 'e': math.e, 'abs': abs, 'round': round
            }
            
            # Security check
            if any(word in expression.lower() for word in ['import', 'exec', 'eval', '__']):
                return "Error: Expression contains unsafe operations"
            
            result = eval(expression, {"__builtins__": {}}, safe_dict)
            return f"Result: {result}"
        except Exception as e:
            return f"Calculation error: {str(e)}"
    
    @function_tool
    async def get_definition(self, context: RunContext, word: str) -> str:
        """Get the definition of a word from a dictionary API."""
        try:
            import requests
            url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
            response = requests.get(url, timeout=5)
            
            if response.status_code != 200:
                return f"Could not find definition for: {word}"
            
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                entry = data[0]
                word_text = entry.get('word', word)
                phonetic = entry.get('phonetic', '')
                meanings = entry.get('meanings', [])
                
                result = [f"'{word_text}' {phonetic}:"]
                for meaning in meanings[:2]:
                    pos = meaning.get('partOfSpeech', '')
                    defs = meaning.get('definitions', [])
                    if defs:
                        result.append(f"\n{pos}: {defs[0].get('definition', '')}")
                
                return "\n".join(result)
            
            return f"No definition found for: {word}"
        except Exception as e:
            return f"Dictionary lookup error: {str(e)}"       
    
    async def on_enter(self):
        """Called when the agent becomes active."""
        logger.info("Agent session started")
        
        # Generate initial greeting
        await self.session.generate_reply(
            instructions="Greet the user warmly and ask how you can help them today."
        )
    
    async def on_exit(self):
        """Called when the agent session ends."""
        logger.info("Agent session ended")


async def entrypoint(ctx: agents.JobContext):
    """Main entry point for the agent worker."""
    
    logger.info(f"Agent started in room: {ctx.room.name}")
    
    # Configure the voice pipeline
    session = AgentSession(
        # Speech-to-Text
        stt=deepgram.STT(
            model="nova-2",
            language="en",
        ),
        
        # Large Language Model
        llm=openai.LLM(
            model=os.getenv("LLM_CHOICE", "gpt-4.1-mini"),
            temperature=0.7,
        ),
        
        # Text-to-Speech
        tts=openai.TTS(
            voice="echo",
            speed=1.0,
        ),
        
        # Voice Activity Detection
        vad=silero.VAD.load(),
        
        # Turn detection strategy
        turn_detection=MultilingualModel(),

        # MCP servers
        mcp_servers=[mcp.MCPServerHTTP(url="http://localhost:8089/mcp",)],
    )
    
    # Start the session
    await session.start(
        room=ctx.room,
        agent=Assistant(),
        # room_input_options=RoomInputOptions(
            # Enable noise cancellation
            # noise_cancellation=noise_cancellation.BVC(),
            # For telephony, use: noise_cancellation.BVCTelephony()
        # ),
        room_output_options=RoomOutputOptions(transcription_enabled=True),
    )
    
    # Handle session events
    @session.on("agent_state_changed")
    def on_state_changed(ev):
        """Log agent state changes."""
        logger.info(f"State: {ev.old_state} -> {ev.new_state}")
    
    @session.on("user_started_speaking")
    def on_user_speaking():
        """Track when user starts speaking."""
        logger.debug("User started speaking")
    
    @session.on("user_stopped_speaking")
    def on_user_stopped():
        """Track when user stops speaking."""
        logger.debug("User stopped speaking")


if __name__ == "__main__":
    # Run the agent using LiveKit CLI
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))