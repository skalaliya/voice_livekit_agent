"""
Simple Universal Agent - Robust & Conversational
------------------------------------------------
A streamlined voice agent that handles ANY question naturally without over-using tools.

Run:
  uv run python -m voice_livekit_agent.simple_universal_agent console
"""

from __future__ import annotations

import os
import json
import requests
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

from livekit import agents
from livekit.agents import Agent, AgentSession, RunContext
from livekit.agents.llm import function_tool
from livekit.plugins import deepgram, openai, silero

load_dotenv(".env")


def _flag(name: str, default: str = "false") -> bool:
    return (os.getenv(name, default) or "").strip().lower() in {"1", "true", "yes", "on"}


def _env(key: str, default: str | None = None) -> str | None:
    return os.getenv(key, default)


def _require_env(keys: list[str]) -> None:
    missing = [k for k in keys if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"Missing: {', '.join(missing)}")


class SimpleUniversalAgent(Agent):
    """A conversational AI that answers ANY question naturally."""
    
    def __init__(self):
        super().__init__(
            instructions=(
                "You are a friendly, helpful AI assistant. "
                "Answer questions naturally and conversationally. "
                "Keep responses brief (1-3 sentences for simple questions). "
                "\n"
                "IMPORTANT:\n"
                "- Respond to greetings normally WITHOUT calling tools\n"
                "- ONLY use tools when you need to calculate, convert, or look something up\n"
                "- For questions you know the answer to, just answer directly\n"
                "- Be warm and conversational\n"
            )
        )
    
    @function_tool
    async def get_current_time(self, context: RunContext) -> str:
        """Get current date and time. Use ONLY when user asks about time/date."""
        now = datetime.now()
        return f"{now.strftime('%A, %B %d, %Y at %I:%M %p')}"
    
    @function_tool
    async def calculate(self, context: RunContext, expression: str) -> str:
        """
        Calculate math. Use ONLY for math questions like "what's 2+2" or "15% of 200".
        NOT for greetings or general questions.
        """
        try:
            import math
            safe = {
                'sqrt': math.sqrt, 'sin': math.sin, 'cos': math.cos,
                'pi': math.pi, 'e': math.e, 'abs': abs
            }
            if any(x in expression.lower() for x in ['import', 'exec', '__']):
                return "Invalid expression"
            result = eval(expression, {"__builtins__": {}}, safe)
            return f"{result}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    @function_tool
    async def convert_units(
        self,
        context: RunContext,
        value: float,
        from_unit: str,
        to_unit: str
    ) -> str:
        """Convert units. Use ONLY when user asks to convert (km to miles, F to C, etc)."""
        try:
            conversions = {
                'm': 1, 'km': 1000, 'mi': 1609.34, 'ft': 0.3048, 'in': 0.0254,
                'kg': 1, 'g': 0.001, 'lb': 0.453592, 'oz': 0.0283495,
                'L': 1, 'ml': 0.001, 'gal': 3.78541,
            }
            
            # Temperature special case
            if from_unit.lower() in ['c', 'f', 'k'] or to_unit.lower() in ['c', 'f', 'k']:
                f, t = from_unit.lower(), to_unit.lower()
                if f == 'c' and t == 'f':
                    return f"{value * 9/5 + 32:.2f}"
                elif f == 'f' and t == 'c':
                    return f"{(value - 32) * 5/9:.2f}"
                elif f == 'c' and t == 'k':
                    return f"{value + 273.15:.2f}"
                elif f == 'k' and t == 'c':
                    return f"{value - 273.15:.2f}"
            
            # Other conversions
            if from_unit in conversions and to_unit in conversions:
                result = value * conversions[from_unit] / conversions[to_unit]
                return f"{result:.4f}"
            
            return "Cannot convert those units"
        except Exception as e:
            return f"Error: {str(e)}"


def _basic_test():
    """Quick LLM test."""
    base = _env("OPENAI_BASE_URL", "http://127.0.0.1:11434/v1")
    model = _env("LLM_MODEL", "llama3.2:3b")
    
    try:
        r = requests.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {_env('OPENAI_API_KEY', 'ollama')}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Say OK"}]
            },
            timeout=30
        )
        r.raise_for_status()
        print(f"✓ LLM OK (model={model})")
    except Exception as e:
        print(f"✗ LLM Error: {e}")
        raise


def _warmup():
    """Warm up model."""
    try:
        base = _env("OPENAI_BASE_URL", "http://127.0.0.1:11434/v1")
        requests.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {_env('OPENAI_API_KEY', 'ollama')}"},
            json={
                "model": _env("LLM_MODEL", "llama3.2:3b"),
                "messages": [{"role": "user", "content": "Hi"}]
            },
            timeout=60
        )
        print("✓ Model warmed up")
    except:
        pass


async def entrypoint(ctx: agents.JobContext):
    """Entry point."""
    
    # Basic test mode
    if _flag("BASIC_TEST", "true"):
        _basic_test()
        return
    
    # Warm up
    if _flag("WARMUP_LLM", "true"):
        _warmup()
    
    # LLM
    llm = openai.LLM(
        model=_env("LLM_MODEL", "llama3.2:3b"),
        base_url=_env("OPENAI_BASE_URL", "http://127.0.0.1:11434/v1"),
        api_key=_env("OPENAI_API_KEY", "ollama"),
        temperature=float(_env("LLM_TEMPERATURE", "0.7")),
    )
    
    # Optional: disable tools
    if not _flag("USE_TOOLS", "true"):
        SimpleUniversalAgent.get_current_time.livekit_tool = False
        SimpleUniversalAgent.calculate.livekit_tool = False
        SimpleUniversalAgent.convert_units.livekit_tool = False
    
    # Audio
    stt = None
    tts = None
    
    try:
        _require_env(["DEEPGRAM_API_KEY"])
        stt = deepgram.STT(model=_env("DEEPGRAM_MODEL", "nova-2"))
        print("✓ STT ready")
    except:
        print("⚠ STT disabled (no DEEPGRAM_API_KEY)")
    
    tts_provider = (_env("TTS_PROVIDER", "deepgram") or "deepgram").lower()
    if tts_provider == "deepgram" and _env("DEEPGRAM_API_KEY"):
        tts = deepgram.TTS(
            model=_env("DEEPGRAM_TTS_MODEL", "aura-asteria-en"),
            api_key=_env("DEEPGRAM_API_KEY"),
        )
        print("✓ TTS ready (Deepgram)")
    elif tts_provider == "openai" and _env("OPENAI_TTS_API_KEY"):
        tts = openai.TTS(
            voice=_env("TTS_VOICE", "alloy"),
            api_key=_env("OPENAI_TTS_API_KEY"),
        )
        print("✓ TTS ready (OpenAI)")
    else:
        print("⚠ TTS disabled")
    
    vad = silero.VAD.load()
    
    # Start session
    session = AgentSession(stt=stt, llm=llm, tts=tts, vad=vad)
    await session.start(room=ctx.room, agent=SimpleUniversalAgent())
    
    # Simple greeting
    await session.generate_reply(
        instructions="Say a brief friendly hello in 1 sentence."
    )


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
