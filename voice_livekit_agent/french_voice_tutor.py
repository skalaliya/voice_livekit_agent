"""
French Voice Tutor (LiveKit + Ollama + Deepgram + OpenAI TTS)
--------------------------------------------------------------
Default: BASIC LLM TEST then exit. Flip BASIC_TEST=false in .env
to enable full voice mode (STT + LLM + TTS + VAD).

Env (minimum for LLM smoke test):
  OPENAI_BASE_URL=http://127.0.0.1:11434/v1
  OPENAI_API_KEY=ollama
  LLM_MODEL=llama3.2:3b
  LLM_TEMPERATURE=0.6
  BASIC_TEST=true
  WARMUP_LLM=true
  WARMUP_TIMEOUT=60

Voice mode (set BASIC_TEST=false and provide):
  DEEPGRAM_API_KEY=...
  OPENAI_TTS_API_KEY=...
  TTS_VOICE=alloy
  USE_TOOLS=false  # turn true if your model handles tool calls well

Run:
  uv run python -m voice_livekit_agent.french_voice_tutor console
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import requests
from dotenv import load_dotenv

from livekit import agents
from livekit.agents import Agent, AgentSession, RunContext
from livekit.agents.llm import function_tool
from livekit.plugins import openai, deepgram, silero


# ---------- env helpers ----------
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


load_dotenv(".env")  # load once


# ---------- tiny phrasebank ----------
PHRASES = {
    "cafe": [
        ("Bonjour, je voudrais un café s’il vous plaît.", "Hello, I’d like a coffee please."),
        ("C’est à emporter ou sur place ?", "Is that takeaway or for here?"),
        ("Vous prenez la carte ?", "Do you take card?"),
    ],
    "travel": [
        ("Où est la gare la plus proche ?", "Where is the nearest train station?"),
        ("À quelle heure part le prochain train pour Lyon ?", "What time is the next train to Lyon?"),
        ("Je cherche un billet aller-retour.", "I’m looking for a return ticket."),
    ],
    "hotel": [
        ("J’ai une réservation au nom de Sam.", "I have a reservation under the name Sam."),
        ("À partir de quelle heure est le check-in ?", "From what time is check-in?"),
        ("Est-ce que le petit déjeuner est inclus ?", "Is breakfast included?"),
    ],
}

LEVELS = ["A1", "A2", "B1", "B2", "C1"]
MODES = ["chat", "roleplay", "quiz", "explain"]
ROLEPLAY_TOPICS = list(PHRASES.keys())


# ---------- agent ----------
class FrenchTutor(Agent):
    """
    A friendly French tutor for an Aussie learner. Speaks mostly French,
    but uses simple English when asked or when explaining tricky bits.
    """

    def __init__(self):
        super().__init__(
            instructions=(
                "Tu es un tuteur de français aimable et patient. "
                "Adapte ton langage au niveau de l’apprenant (A1 à C1). "
                "Parle surtout en français, mais utilise un peu d’anglais simple pour expliquer si nécessaire. "
                "Corrige doucement, donne des exemples naturels, et propose des mini-exercices. "
                "Si l’apprenant dit 'switch to English', réponds en anglais. "
                "Garde les réponses courtes et parlées, comme une conversation."
            )
        )
        self.level = "A1"
        self.mode = "chat"
        self.topic = "cafe"
        self.vocab: list[dict] = []  # [{word, translation, example}]
        self._persist_file = "french_progress.json"
        self._load_progress()

    # --------- progress persistence (lightweight) ----------
    def _load_progress(self):
        try:
            if os.path.exists(self._persist_file):
                with open(self._persist_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.level = data.get("level", self.level)
                self.mode = data.get("mode", self.mode)
                self.topic = data.get("topic", self.topic)
                self.vocab = data.get("vocab", [])
        except Exception:
            pass

    def _save_progress(self):
        try:
            data = {
                "level": self.level,
                "mode": self.mode,
                "topic": self.topic,
                "vocab": self.vocab,
                "saved_at": datetime.now().isoformat(timespec="seconds"),
            }
            with open(self._persist_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # --------- tools (toggle with USE_TOOLS) ----------
    @function_tool
    async def set_level(self, context: RunContext, level: str) -> str:
        """Set CEFR level: A1, A2, B1, B2, C1."""
        lvl = level.upper().strip()
        if lvl not in LEVELS:
            return f"Niveau inconnu: {level}. Choisis parmi {', '.join(LEVELS)}."
        self.level = lvl
        self._save_progress()
        return f"Niveau réglé sur {lvl}. Allons-y !"

    @function_tool
    async def set_mode(self, context: RunContext, mode: str, topic: str | None = None) -> str:
        """Set mode: chat, roleplay (topics: cafe, travel, hotel), quiz, explain."""
        md = mode.lower().strip()
        if md not in MODES:
            return f"Mode inconnu: {mode}. Choisis parmi {', '.join(MODES)}."
        self.mode = md
        if md == "roleplay" and topic:
            tp = topic.lower().strip()
            if tp in ROLEPLAY_TOPICS:
                self.topic = tp
        self._save_progress()
        if self.mode == "roleplay":
            return f"Mode roleplay activé, thème: {self.topic}."
        return f"Mode réglé sur {self.mode}."

    @function_tool
    async def phrase_pack(self, context: RunContext, topic: str) -> str:
        """Get a short phrase pack for a roleplay topic (cafe, travel, hotel)."""
        tp = topic.lower().strip()
        if tp not in PHRASES:
            return f"Sujet inconnu: {topic}. Choisis parmi {', '.join(ROLEPLAY_TOPICS)}."
        items = PHRASES[tp]
        out = [f"Phrases utiles pour {tp}:"]
        for fr, en in items:
            out.append(f"- {fr}  ({en})")
        return "\n".join(out)

    @function_tool
    async def add_vocab(self, context: RunContext, word: str, translation: str, example: str | None = None) -> str:
        """Add a vocab item to your list."""
        self.vocab.append({"word": word, "translation": translation, "example": example or ""})
        self._save_progress()
        return f"Ajouté: {word} → {translation}."

    @function_tool
    async def list_vocab(self, context: RunContext) -> str:
        """List your saved vocab items."""
        if not self.vocab:
            return "Ta liste de vocabulaire est vide. Dis 'add vocab' pour commencer."
        out = ["Vocabulaire enregistré:"]
        for i, it in enumerate(self.vocab, 1):
            ex = f" | ex: {it['example']}" if it.get("example") else ""
            out.append(f"{i}. {it['word']} → {it['translation']}{ex}")
        return "\n".join(out)


# ---------- LLM-only smoke test ----------
def _basic_llm_check() -> None:
    base = _env("OPENAI_BASE_URL", "http://127.0.0.1:11434/v1")
    api = _env("OPENAI_API_KEY", "ollama")
    model = _env("LLM_CHOICE") or _env("LLM_MODEL", "llama3.2:3b")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a concise, friendly French tutor."},
            {"role": "user", "content": "Say bonjour in one short French sentence."},
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


# ---------- warm-up for Ollama ----------
def _warmup_ollama():
    base = _env("OPENAI_BASE_URL", "http://127.0.0.1:11434/v1")
    api = _env("OPENAI_API_KEY", "ollama")
    model = _env("LLM_CHOICE") or _env("LLM_MODEL", "llama3.2:3b")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a concise assistant."},
            {"role": "user", "content": "Reply with just: prêt."},
        ],
    }
    r = requests.post(
        f"{base}/chat/completions",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api}"},
        data=json.dumps(payload),
        timeout=float(_env("WARMUP_TIMEOUT", "60")),
    )
    r.raise_for_status()


# ---------- entrypoint ----------
async def entrypoint(ctx: agents.JobContext):
    """Entry point for the tutor."""

    # 1) BASIC TEST path
    if _flag("BASIC_TEST", "true"):
        _basic_llm_check()
        return

    # 2) Warm up model to avoid first-token timeouts
    if _flag("WARMUP_LLM", "true"):
        _warmup_ollama()

    # 3) LLM via Ollama
    llm = openai.LLM(
        model=_env("LLM_CHOICE") or _env("LLM_MODEL", "llama3.2:3b"),
        base_url=_env("OPENAI_BASE_URL", "http://127.0.0.1:11434/v1"),
        api_key=_env("OPENAI_API_KEY", "ollama"),
        temperature=float(_env("LLM_TEMPERATURE", "0.6")),
    )

    # Optional: disable function tools for smaller OSS models
    if not _flag("USE_TOOLS", "false"):
        FrenchTutor.set_level.livekit_tool = False
        FrenchTutor.set_mode.livekit_tool = False
        FrenchTutor.phrase_pack.livekit_tool = False
        FrenchTutor.add_vocab.livekit_tool = False
        FrenchTutor.list_vocab.livekit_tool = False

    # 4) Audio
    _require_env(["DEEPGRAM_API_KEY", "OPENAI_TTS_API_KEY"])
    stt = deepgram.STT(model=_env("DEEPGRAM_MODEL", "nova-2"))
    tts = openai.TTS(voice=_env("TTS_VOICE", "alloy"), api_key=_env("OPENAI_TTS_API_KEY"))
    vad = silero.VAD.load()

    # 5) Start session
    session = AgentSession(stt=stt, llm=llm, tts=tts, vad=vad)
    await session.start(room=ctx.room, agent=FrenchTutor())

    # Initial greeting: Aussie warmth, then in French at learner level
    await session.generate_reply(
        instructions=(
            "Greet the user in friendly Australian English, mention you’re a French tutor, "
            "then continue in French at their current level (default A1). "
            "Offer modes: roleplay (café, travel, hotel), quiz, explain. "
            "Be brief and conversational."
        )
    )


# ---------- runner ----------
if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
