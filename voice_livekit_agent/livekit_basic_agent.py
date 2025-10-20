"""
LiveKit Voice Agent - Quick Start (Ollama + Deepgram + OpenAI TTS)
-------------------------------------------------------------------
Default: run a BASIC LLM TEST then exit. Flip BASIC_TEST=false in .env
to enable the full voice pipeline (STT + LLM + TTS + VAD).

Required env (LLM only smoke test):
  OPENAI_BASE_URL=http://127.0.0.1:11434/v1
  OPENAI_API_KEY=ollama
  LLM_MODEL=llama3.2:3b
  BASIC_TEST=true

Voice mode (when BASIC_TEST=false):
  DEEPGRAM_API_KEY=...
  OPENAI_TTS_API_KEY=...
  TTS_VOICE=alloy

Optional:
  USE_TOOLS=true|false     # default false for OSS models
  LLM_TEMPERATURE=0.6
  DEEPGRAM_MODEL=nova-2
  TTS_PROVIDER=openai|deepgram
  DEEPGRAM_TTS_MODEL=aura-2-andromeda-en
  OPENAI_TTS_BASE_URL=https://api.openai.com/v1
  WARMUP_LLM=true|false    # default true
  WARMUP_TIMEOUT=60

Run:
  uv run python -m voice_livekit_agent.livekit_basic_agent console
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import requests
from dotenv import load_dotenv

from livekit import agents
from livekit.agents import Agent, AgentSession, RunContext, io
from livekit.agents.llm import function_tool
from livekit.plugins import openai, deepgram, silero


# -------------------------
# env + helpers
# -------------------------
def _flag(name: str, default: str = "false") -> bool:
    return (os.getenv(name, default) or "").strip().lower() in {"1", "true", "yes", "on"}

def _env(key: str, default: str | None = None) -> str | None:
    return os.getenv(key, default)

def _require_env(keys: list[str]) -> None:
    missing = [k for k in keys if not os.getenv(k)]
    if missing:
        raise RuntimeError(
            "Missing required environment variables: "
            + ", ".join(missing)
            + "\nTip: add them to your .env (do NOT commit secrets)."
        )

def _disable_tool(func) -> None:
    """Remove LiveKit tool metadata so the model cannot invoke the function."""
    if hasattr(func, "__livekit_tool_info"):
        delattr(func, "__livekit_tool_info")

# load .env once at import
load_dotenv(".env")


# -------------------------
# Agent definition
# -------------------------
class Assistant(Agent):
    """Basic voice assistant with Airbnb booking capabilities."""

    def __init__(self):
        super().__init__(
            instructions=(
                "You are a helpful and friendly Airbnb voice assistant. "
                "Chat naturally with the user and keep conversations flowing. "
                "Only call the Airbnb tools when the user clearly asks for listings, availability, or booking help."
            )
        )

        self.airbnbs = {
            "san francisco": [
                {
                    "id": "sf001",
                    "name": "Cozy Downtown Loft",
                    "address": "123 Market Street, San Francisco, CA",
                    "price": 150,
                    "amenities": ["WiFi", "Kitchen", "Workspace"],
                },
                {
                    "id": "sf002",
                    "name": "Victorian House with Bay Views",
                    "address": "456 Castro Street, San Francisco, CA",
                    "price": 220,
                    "amenities": ["WiFi", "Parking", "Washer/Dryer", "Bay Views"],
                },
                {
                    "id": "sf003",
                    "name": "Modern Studio near Golden Gate",
                    "address": "789 Presidio Avenue, San Francisco, CA",
                    "price": 180,
                    "amenities": ["WiFi", "Kitchen", "Pet Friendly"],
                },
            ],
            "new york": [
                {
                    "id": "ny001",
                    "name": "Brooklyn Brownstone Apartment",
                    "address": "321 Bedford Avenue, Brooklyn, NY",
                    "price": 175,
                    "amenities": ["WiFi", "Kitchen", "Backyard Access"],
                },
                {
                    "id": "ny002",
                    "name": "Manhattan Skyline Penthouse",
                    "address": "555 Fifth Avenue, Manhattan, NY",
                    "price": 350,
                    "amenities": ["WiFi", "Gym", "Doorman", "City Views"],
                },
                {
                    "id": "ny003",
                    "name": "Artsy East Village Loft",
                    "address": "88 Avenue A, Manhattan, NY",
                    "price": 195,
                    "amenities": ["WiFi", "Washer/Dryer", "Exposed Brick"],
                },
            ],
            "los angeles": [
                {
                    "id": "la001",
                    "name": "Venice Beach Bungalow",
                    "address": "234 Ocean Front Walk, Venice, CA",
                    "price": 200,
                    "amenities": ["WiFi", "Beach Access", "Patio"],
                },
                {
                    "id": "la002",
                    "name": "Hollywood Hills Villa",
                    "address": "777 Mulholland Drive, Los Angeles, CA",
                    "price": 400,
                    "amenities": ["WiFi", "Pool", "City Views", "Hot Tub"],
                },
            ],
        }
        self.bookings = []

    @function_tool
    async def get_current_date_and_time(self, context: RunContext) -> str:
        current_datetime = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        return f"The current date and time is {current_datetime}"

    @function_tool
    async def search_airbnbs(self, context: RunContext, city: str) -> str:
        city_lower = city.lower()
        if city_lower not in self.airbnbs:
            return (
                f"Sorry, I don't have any Airbnb listings for {city} at the moment. "
                "Available cities are: San Francisco, New York, and Los Angeles."
            )
        listings = self.airbnbs[city_lower]
        out = [f"Found {len(listings)} Airbnbs in {city}:\n"]
        for l in listings:
            out.append(
                f"• {l['name']}\n"
                f"  Address: {l['address']}\n"
                f"  Price: ${l['price']} per night\n"
                f"  Amenities: {', '.join(l['amenities'])}\n"
                f"  ID: {l['id']}\n"
            )
        return "\n".join(out)

    @function_tool
    async def book_airbnb(
        self,
        context: RunContext,
        airbnb_id: str,
        guest_name: str,
        check_in_date: str,
        check_out_date: str,
    ) -> str:
        airbnb = None
        for city_listings in self.airbnbs.values():
            for listing in city_listings:
                if listing["id"] == airbnb_id:
                    airbnb = listing
                    break
            if airbnb:
                break

        if not airbnb:
            return (
                f"Sorry, I couldn't find an Airbnb with ID {airbnb_id}. "
                "Please search for available listings first."
            )

        booking = {
            "confirmation_number": f"BK{len(self.bookings) + 1001}",
            "airbnb_name": airbnb["name"],
            "address": airbnb["address"],
            "guest_name": guest_name,
            "check_in": check_in_date,
            "check_out": check_out_date,
            "total_price": airbnb["price"],
        }
        self.bookings.append(booking)

        return (
            "✓ Booking confirmed!\n\n"
            f"Confirmation Number: {booking['confirmation_number']}\n"
            f"Property: {booking['airbnb_name']}\n"
            f"Address: {booking['address']}\n"
            f"Guest: {booking['guest_name']}\n"
            f"Check-in: {booking['check_in']}\n"
            f"Check-out: {booking['check_out']}\n"
            f"Nightly Rate: ${booking['total_price']}\n\n"
            "You'll receive a confirmation email shortly. Have a great stay!"
        )


class ConsoleTextSink(io.TextOutput):
    """Mirror agent replies into the terminal while preserving the existing sink chain."""

    def __init__(
        self,
        *,
        label: str = "console_logger",
        next_in_chain: io.TextOutput | None = None,
    ) -> None:
        super().__init__(label=label, next_in_chain=next_in_chain)
        self._buffer: list[str] = []

    async def capture_text(self, text: str) -> None:  # type: ignore[override]
        self._buffer.append(text)
        print(f"[Agent] {text}", end="", flush=True)
        if self.next_in_chain:
            await self.next_in_chain.capture_text(text)

    def flush(self) -> None:  # type: ignore[override]
        if self._buffer:
            print()
            self._buffer.clear()
        if self.next_in_chain:
            self.next_in_chain.flush()


# -------------------------
# LLM-only smoke test (no audio)
# -------------------------
def _basic_llm_check() -> None:
    base = _env("OPENAI_BASE_URL", "http://127.0.0.1:11434/v1")
    api = _env("OPENAI_API_KEY", "ollama")
    model = _env("LLM_CHOICE") or _env("LLM_MODEL", "llama3.2:3b")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a concise, friendly assistant."},
            {"role": "user", "content": "Say hello in one short sentence."},
        ],
    }
    r = requests.post(
        f"{base}/chat/completions",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api}"},
        data=json.dumps(payload),
        timeout=60,
    )
    r.raise_for_status()
    msg = r.json()["choices"][0]["message"]["content"]
    print(f"LLM CHECK OK (model={model}, base={base}) ->", msg)


# -------------------------
# Warm-up helper (for Ollama first-token latency)
# -------------------------
def _warmup_ollama():
    base = _env("OPENAI_BASE_URL", "http://127.0.0.1:11434/v1")
    api = _env("OPENAI_API_KEY", "ollama")
    model = _env("LLM_CHOICE") or _env("LLM_MODEL", "llama3.2:3b")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a concise assistant."},
            {"role": "user", "content": "Reply with just: ready."}
        ],
    }
    r = requests.post(
        f"{base}/chat/completions",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api}"},
        data=json.dumps(payload),
        timeout=float(_env("WARMUP_TIMEOUT", "60")),
    )
    r.raise_for_status()


# -------------------------
# LiveKit entrypoint (with warm-up)
# -------------------------
async def entrypoint(ctx: agents.JobContext):
    """Entry point for the agent."""

    # 1) BASIC TEST (default true): just ping the LLM and exit
    if _flag("BASIC_TEST", "true"):
        _basic_llm_check()
        return

    # 2) Warm up Ollama once so first real request doesn't timeout
    if _flag("WARMUP_LLM", "true"):
        _warmup_ollama()

    # 3) LLM via Ollama (OpenAI-compatible)
    llm = openai.LLM(
        model=_env("LLM_CHOICE") or _env("LLM_MODEL", "llama3.2:3b"),
        base_url=_env("OPENAI_BASE_URL", "http://127.0.0.1:11434/v1"),
        api_key=_env("OPENAI_API_KEY", "ollama"),
        temperature=float(_env("LLM_TEMPERATURE", "0.6")),
    )

    # Optional: disable function tools unless explicitly enabled
    if not _flag("USE_TOOLS", "false"):
        _disable_tool(Assistant.get_current_date_and_time)
        _disable_tool(Assistant.search_airbnbs)
        _disable_tool(Assistant.book_airbnb)

    # 4) Audio stack (requires keys)
    _require_env(["DEEPGRAM_API_KEY"])
    stt = deepgram.STT(model=_env("DEEPGRAM_MODEL", "nova-2"))
    tts_provider = (_env("TTS_PROVIDER", "openai") or "openai").strip().lower()
    if tts_provider == "deepgram":
        tts = deepgram.TTS(
            model=_env("DEEPGRAM_TTS_MODEL", "aura-2-andromeda-en"),
            api_key=_env("DEEPGRAM_API_KEY"),
        )
    elif tts_provider in {"none", "off", "disabled"}:
        tts = None
    else:
        _require_env(["OPENAI_TTS_API_KEY"])
        tts_base_url = _env("OPENAI_TTS_BASE_URL")
        if not tts_base_url:
            # Force the TTS client to use OpenAI's public endpoint so it doesn't inherit the
            # LLM base (e.g., Ollama) via OPENAI_BASE_URL which lacks the audio API surface.
            tts_base_url = "https://api.openai.com/v1"
        tts = openai.TTS(
            voice=_env("TTS_VOICE", "alloy"),
            api_key=_env("OPENAI_TTS_API_KEY"),
            base_url=tts_base_url,
        )
    vad = silero.VAD.load()

    # 5) Start the voice session
    session = AgentSession(
        stt=stt,
        llm=llm,
        tts=tts,
        vad=vad,
    )
    existing_transcript_sink = session.output.transcription
    session.output.transcription = ConsoleTextSink(next_in_chain=existing_transcript_sink)

    await session.start(room=ctx.room, agent=Assistant())

    # Initial greeting
    await session.generate_reply(
        instructions="G’day! I’m your Airbnb helper. How can I help?"
    )


# -------------------------
# Runner
# -------------------------
if __name__ == "__main__":
    # Use the LiveKit CLI runner (subcommands: console, dev, start, connect)
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
