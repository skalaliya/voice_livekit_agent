"""
French Voice Tutor PLUS (LiveKit + Ollama + Deepgram + OpenAI TTS)
-------------------------------------------------------------------
Adds:
  • Spaced-repetition vocab quiz (Leitner-style boxes)
  • Pronunciation practice with transcript comparison + hints

Default behaviour:
  BASIC_TEST=true -> run a quick LLM smoke test then exit.
Flip BASIC_TEST=false in .env for full voice mode.

Env (LLM only):
  OPENAI_BASE_URL=http://127.0.0.1:11434/v1
  OPENAI_API_KEY=ollama
  LLM_MODEL=llama3.2:3b
  LLM_TEMPERATURE=0.6
  BASIC_TEST=true
  WARMUP_LLM=true
  WARMUP_TIMEOUT=60

Voice mode (set BASIC_TEST=false):
  DEEPGRAM_API_KEY=...
  OPENAI_TTS_API_KEY=...
  TTS_VOICE=alloy
  USE_TOOLS=true        # enable quiz + pronunciation tools
  DEEPGRAM_MODEL=nova-2

SRS export (optional):
  SRS_EXPORT_DIR=~/.french_tutor/exports
  SRS_AUTO_EXPORT=true
  SRS_EXPORT_FORMAT=csv
  SRS_STATE_FILE=french_progress_plus.json

Run:
  uv run python -m voice_livekit_agent.french_voice_tutor_plus console
"""

from __future__ import annotations

import csv
import json
import os
import random
import re
import pathlib
import unicodedata
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

from livekit import agents
from livekit.agents import Agent, AgentSession, RunContext
from livekit.agents.llm import function_tool
from livekit.plugins import deepgram, openai, silero


# -------------------------
# Env + helpers
# -------------------------
def _flag(name: str, default: str = "false") -> bool:
    return (os.getenv(name, default) or "").strip().lower() in {"1", "true", "yes", "on"}


def _env(key: str, default: str | None = None) -> str | None:
    return os.getenv(key, default)


def _require_env(keys: List[str]) -> None:
    missing = [k for k in keys if not os.getenv(k)]
    if missing:
        raise RuntimeError(
            "Missing required environment variables: "
            + ", ".join(missing)
            + "\nTip: add them to your .env (do NOT commit secrets)."
        )


load_dotenv(".env")  # once


# -------------------------
# Phrasebank (for roleplay + pronunciation)
# -------------------------
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
MODES = ["chat", "roleplay", "quiz", "explain", "pronounce"]
ROLEPLAY_TOPICS = list(PHRASES.keys())


# -------------------------
# Text utils (accents / WER / diffs)
# -------------------------
_WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ'-]+", re.UNICODE)


def _strip_accents(text: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFD", text)
        if unicodedata.category(ch) != "Mn"
    )


def _tokenize(text: str) -> List[str]:
    return [m.group(0).lower() for m in _WORD_RE.finditer(text)]


def _levenshtein(a: List[str], b: List[str]) -> int:
    # token-level edit distance
    dp = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        prev = dp[0]
        dp[0] = i
        for j, y in enumerate(b, 1):
            cur = dp[j]
            dp[j] = min(
                dp[j] + 1,  # deletion
                dp[j - 1] + 1,  # insertion
                prev + (0 if x == y else 1),  # substitution
            )
            prev = cur
    return dp[-1]


def _wer(ref: str, hyp: str) -> float:
    r = _tokenize(_strip_accents(ref))
    h = _tokenize(_strip_accents(hyp))
    if not r:
        return 0.0
    return _levenshtein(r, h) / len(r)


def _accent_mismatches(ref: str, hyp: str) -> List[Tuple[str, str]]:
    # return tokens that match without accents but differ with accents
    r_tokens = _tokenize(ref)
    h_tokens = _tokenize(hyp)
    mismatches: List[Tuple[str, str]] = []
    for rt, ht in zip(r_tokens, h_tokens):
        if _strip_accents(rt) == _strip_accents(ht) and rt != ht:
            mismatches.append((rt, ht))
    return mismatches


# -------------------------
# Spaced repetition scheduling (Leitner 1..5)
# -------------------------
BOX_DELAYS_DAYS = {1: 1, 2: 2, 3: 4, 4: 7, 5: 15}


def _next_due(box: int, now: Optional[datetime] = None) -> str:
    now = now or datetime.now()
    days = BOX_DELAYS_DAYS.get(max(1, min(5, box)), 1)
    return (now + timedelta(days=days)).isoformat(timespec="seconds")


# -------------------------
# The Agent
# -------------------------
class FrenchTutorPlus(Agent):
    """
    Friendly French tutor for an Aussie learner.
    Adds:
      - spaced repetition vocab quiz
      - pronunciation practice
    """

    def __init__(self):
        super().__init__(
            instructions=(
                "Tu es un tuteur de français patient et chaleureux. "
                "Parle surtout en français, adapte-toi au niveau (A1 à C1). "
                "Corrige doucement, donne des exemples naturels. "
                "Utilise les outils (si disponibles) pour quiz/prononciation/vocab."
            )
        )
        self.level = "A1"
        self.mode = "chat"
        self.topic = "cafe"

        # vocab items: {word, translation, example, box, next_due, history:[]}
        self.vocab: List[Dict[str, Any]] = []
        # quiz state
        self._quiz_queue: List[int] = []  # indices into self.vocab
        self._quiz_current: Optional[int] = None
        self._quiz_direction: str = "en2fr"  # or "fr2en"

        # pronunciation target
        self._pron_target: Optional[str] = None

        # SRS persistence & export
        self._state_file = _env("SRS_STATE_FILE", "french_progress_plus.json")
        self._export_dir = pathlib.Path(
            os.path.expanduser(_env("SRS_EXPORT_DIR", "~/.french_tutor/exports"))
        )
        self._auto_export = _flag("SRS_AUTO_EXPORT", "true")
        self._export_format = (_env("SRS_EXPORT_FORMAT", "csv") or "csv").lower()
        self._export_dir.mkdir(parents=True, exist_ok=True)

        self._persist_file = self._state_file
        self._load_progress()

    # --------- persistence ----------
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

    def _export_snapshot(self, reason: str = "manual") -> None:
        """Write CSV/JSON snapshot of current vocab with due info."""
        try:
            now = datetime.now()
            stamp = now.strftime("%Y-%m-%d")
            rows: List[Dict[str, Any]] = []
            for it in self.vocab:
                overdue_days: Any
                try:
                    due = datetime.fromisoformat(it.get("next_due", "1970-01-01T00:00:00"))
                    overdue_days = (now - due).days if now > due else 0
                except Exception:
                    overdue_days = ""
                rows.append(
                    {
                        "word": it.get("word", ""),
                        "translation": it.get("translation", ""),
                        "example": it.get("example", ""),
                        "box": it.get("box", 1),
                        "next_due": it.get("next_due", ""),
                        "overdue_days": overdue_days,
                    }
                )

            if self._export_format in {"csv", "both"}:
                csv_path = self._export_dir / f"srs_{stamp}.csv"
                with open(csv_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(
                        f,
                        fieldnames=["word", "translation", "example", "box", "next_due", "overdue_days"],
                    )
                    writer.writeheader()
                    writer.writerows(rows)

            if self._export_format in {"json", "both"}:
                json_path = self._export_dir / f"srs_{stamp}.json"
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "exported_at": now.isoformat(timespec="seconds"),
                            "level": self.level,
                            "mode": self.mode,
                            "topic": self.topic,
                            "vocab": rows,
                            "reason": reason,
                        },
                        f,
                        ensure_ascii=False,
                        indent=2,
                    )
        except Exception:
            # keep tutor resilient if disk write fails
            pass

    def _maybe_auto_export(self, reason: str) -> None:
        if self._auto_export:
            self._export_snapshot(reason)

    # --------- core tools ----------
    @function_tool
    async def set_level(self, context: RunContext, level: str) -> str:
        """Set CEFR level: A1, A2, B1, B2, C1."""
        lvl = level.upper().strip()
        if lvl not in LEVELS:
            return f"Niveau inconnu: {level}. Choisis parmi {', '.join(LEVELS)}."
        self.level = lvl
        self._save_progress()
        self._maybe_auto_export("set_level")
        return f"Niveau réglé sur {lvl}. On continue !"

    @function_tool
    async def set_mode(self, context: RunContext, mode: str, topic: str | None = None) -> str:
        """Set mode: chat, roleplay (cafe|travel|hotel), quiz, explain, pronounce."""
        md = mode.lower().strip()
        if md not in MODES:
            return f"Mode inconnu: {mode}. Choisis parmi {', '.join(MODES)}."
        self.mode = md
        if md == "roleplay" and topic:
            tp = topic.lower().strip()
            if tp in ROLEPLAY_TOPICS:
                self.topic = tp
        self._save_progress()
        self._maybe_auto_export("set_mode")
        if self.mode == "roleplay":
            return f"Mode roleplay activé, thème: {self.topic}."
        if self.mode == "pronounce":
            return "Mode prononciation activé. Dis 'donne-moi une phrase' pour commencer."
        if self.mode == "quiz":
            return "Mode quiz activé. Dis 'start quiz' pour lancer un quiz vocabulaire."
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

    # --------- vocab management ----------
    @function_tool
    async def add_vocab(self, context: RunContext, word: str, translation: str, example: str | None = None) -> str:
        """Add a vocab item with spaced-repetition fields."""
        item = {
            "word": word.strip(),
            "translation": translation.strip(),
            "example": (example or "").strip(),
            "box": 1,
            "next_due": _next_due(1),
            "history": [],
        }
        self.vocab.append(item)
        self._save_progress()
        self._maybe_auto_export("add_vocab")
        return f"Ajouté: {item['word']} → {item['translation']}. Première révision demain."

    @function_tool
    async def list_vocab(self, context: RunContext) -> str:
        """List saved vocab items with due info."""
        if not self.vocab:
            return "Ta liste est vide. Utilise 'add_vocab' pour commencer."
        out = ["Vocabulaire enregistré:"]
        for i, it in enumerate(self.vocab, 1):
            out.append(f"{i}. {it['word']} → {it['translation']} | box {it['box']} | due {it['next_due']}")
        return "\n".join(out)

    @function_tool
    async def due_words(
        self,
        context: RunContext,
        top_k: int = 5,
        include_examples: bool = False,
    ) -> str:
        """
        Tell me what's due today for spaced repetition.
        Returns the top-k due vocab items with box and due time.
        """
        due_idxs = self._due_indices()
        if not due_idxs:
            return (
                "Aucune révision urgente aujourd’hui. "
                "Tu peux lancer un petit quiz pour t’échauffer, dis: "
                "« start quiz »."
            )

        due_idxs.sort(
            key=lambda i: (
                self.vocab[i].get("box", 1),
                self.vocab[i].get("next_due", ""),
            )
        )

        lines: List[str] = []
        limit = max(1, top_k)
        for idx in due_idxs[:limit]:
            item = self.vocab[idx]
            word = item.get("word", "?")
            translation = item.get("translation", "?")
            box = item.get("box", 1)
            example = item.get("example", "")
            if include_examples and example:
                line = f"• {word} → {translation}, boîte {box}. Exemple: {example}"
            else:
                line = f"• {word} → {translation}, boîte {box}"
            lines.append(line)

        header = f"{len(lines)} mot(s) à réviser maintenant:"
        tail = "Dis « start quiz » pour commencer."
        return header + "\n" + "\n".join(lines) + "\n" + tail

    # --------- spaced repetition quiz ----------
    def _due_indices(self, now: Optional[datetime] = None) -> List[int]:
        now = now or datetime.now()
        idxs = []
        for i, it in enumerate(self.vocab):
            try:
                due = datetime.fromisoformat(it.get("next_due", "1970-01-01T00:00:00"))
            except Exception:
                due = datetime(1970, 1, 1)
            if due <= now:
                idxs.append(i)
        return idxs

    @function_tool
    async def start_quiz(self, context: RunContext, count: int = 5, direction: str = "en2fr") -> str:
        """
        Start a spaced-repetition quiz.
        direction: 'en2fr' (default) or 'fr2en'
        """
        if not self.vocab:
            return "Tu n’as pas encore de vocabulaire. Ajoute quelques mots d’abord."
        self._quiz_direction = direction.lower().strip() if direction else "en2fr"

        due = self._due_indices()
        if not due:
            # if nothing due, sample a few from box 1 to keep practice going
            due = [i for i, _ in sorted(enumerate(self.vocab), key=lambda t: t[1]["box"])]
        random.shuffle(due)
        self._quiz_queue = due[: max(1, min(count, len(due)))]
        self._quiz_current = None

        return await self.next_question(context)

    @function_tool
    async def next_question(self, context: RunContext) -> str:
        """Serve next question in the current quiz."""
        if not self._quiz_queue:
            self._quiz_current = None
            return "Quiz terminé, bravo ! On révisera encore plus tard."
        self._quiz_current = self._quiz_queue.pop(0)
        it = self.vocab[self._quiz_current]
        if self._quiz_direction == "en2fr":
            return f"Traduction en français: “{it['translation']}”."
        else:
            return f"Traduction en anglais: “{it['word']}”."

    @function_tool
    async def answer_quiz(self, context: RunContext, user_answer: str) -> str:
        """Grade the user's answer, update SRS box/next_due, and return feedback + next prompt."""
        if self._quiz_current is None:
            return "Pas de question en cours. Dis 'start quiz' pour commencer."

        it = self.vocab[self._quiz_current]
        # normalise for fuzzy match
        ans = _strip_accents(user_answer).lower().strip()
        if self._quiz_direction == "en2fr":
            gold = _strip_accents(it["word"]).lower()
            show_gold = it["word"]
        else:
            gold = _strip_accents(it["translation"]).lower()
            show_gold = it["translation"]

        # token-level distance on words
        dist = _levenshtein(_tokenize(gold), _tokenize(ans))
        max_len = max(1, len(_tokenize(gold)))
        ok = (dist / max_len) <= 0.34  # forgiving threshold for small models + STT noise

        # update Leitner box
        now = datetime.now()
        if ok:
            it["box"] = min(5, it.get("box", 1) + 1)
            it["history"].append({"t": now.isoformat(timespec="seconds"), "ok": True, "input": user_answer})
            it["next_due"] = _next_due(it["box"], now)
            verdict = f"✅ Bien joué ! Réponse attendue: “{show_gold}”."
        else:
            it["box"] = 1
            it["history"].append({"t": now.isoformat(timespec="seconds"), "ok": False, "input": user_answer})
            it["next_due"] = _next_due(1, now)
            verdict = f"❌ Presque. La bonne réponse est: “{show_gold}”."

        self._save_progress()
        self._maybe_auto_export("answer_quiz")

        # chain next question
        nxt = await self.next_question(context)
        return f"{verdict}\nProchaine: {nxt}"

    # --------- pronunciation practice ----------
    @function_tool
    async def give_sentence(self, context: RunContext, topic: str | None = None) -> str:
        """Choose a French sentence for pronunciation (from phrasebank)."""
        tp = (topic or self.topic).lower()
        if tp not in PHRASES:
            tp = random.choice(ROLEPLAY_TOPICS)
        fr, en = random.choice(PHRASES[tp])
        self._pron_target = fr
        return f"Répète après moi: “{fr}” (thème: {tp})."

    @function_tool
    async def check_pronunciation(self, context: RunContext, heard: str) -> str:
        """Compare user's spoken line to the target sentence and give hints."""
        if not self._pron_target:
            return "Pas de phrase cible encore. Dis 'give_sentence' d’abord."
        target = self._pron_target

        w = _wer(target, heard)
        mism = _accent_mismatches(target, heard)
        tips = []

        if w <= 0.2:
            level = "Excellent — très clair !"
        elif w <= 0.35:
            level = "Bien — compréhensible avec quelques petites erreurs."
        elif w <= 0.5:
            level = "Correct — retravaillons l’articulation."
        else:
            level = "Difficile à comprendre — on va le décomposer."

        if mism:
            # list a few accent mismatches
            ex = ", ".join([f"{a}→{b}" for a, b in mism[:3]])
            tips.append(f"Accents à surveiller: {ex}")

        # common French pitfalls: silent final letters, liaison hints
        t_tokens = _tokenize(target)
        h_tokens = _tokenize(heard)
        if len(h_tokens) and len(t_tokens) and h_tokens[0] == "je" and t_tokens[0] == "j’ai":
            tips.append("Astuce: “j’ai” se prononce comme 'jé', pas 'je'.")
        if any(t in target for t in ["est-ce que", "vous", "un", "une"]):
            tips.append("Astuce: fais attention aux liaisons (ex: 'vous‿avez', 'est-ce').")

        score = int(max(0, 100 * (1 - w)))
        tip_text = ("\n".join(tips)) if tips else "Continuité parfaite, on augmente la vitesse progressivement."
        return f"{level}\nScore: {score}/100 (WER≈{w:.2f})\n{tip_text}"
    # --------- end tools ---------


# -------------------------
# LLM smoke test (no audio)
# -------------------------
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
        json=payload,
        timeout=60,
    )
    r.raise_for_status()
    msg = r.json()["choices"][0]["message"]["content"]
    print(f"LLM CHECK OK (model={model}, base={base}) ->", msg)


# -------------------------
# Warm-up for Ollama (avoid first-token timeouts)
# -------------------------
def _warmup_ollama():
    base = _env("OPENAI_BASE_URL", "http://127.0.0.1:11434/v1")
    api = _env("OPENAI_API_KEY", "ollama")
    model = _env("LLM_CHOICE") or _env("LLM_MODEL", "llama3.2:3b")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a concise assistant."},
            {"role": "user", "content": "Reply with just: prêt."}
        ],
    }
    r = requests.post(
        f"{base}/chat/completions",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api}"},
        json=payload,
        timeout=float(_env("WARMUP_TIMEOUT", "60")),
    )
    r.raise_for_status()


# -------------------------
# LiveKit entrypoint
# -------------------------
async def entrypoint(ctx: agents.JobContext):
    # 1) BASIC TEST path
    if _flag("BASIC_TEST", "true"):
        _basic_llm_check()
        return

    # 2) Warm-up
    if _flag("WARMUP_LLM", "true"):
        _warmup_ollama()

    # 3) LLM via Ollama (OpenAI-compatible)
    llm = openai.LLM(
        model=_env("LLM_CHOICE") or _env("LLM_MODEL", "llama3.2:3b"),
        base_url=_env("OPENAI_BASE_URL", "http://127.0.0.1:11434/v1"),
        api_key=_env("OPENAI_API_KEY", "ollama"),
        temperature=float(_env("LLM_TEMPERATURE", "0.6")),
    )

    # Enable/disable tools for small models
    if not _flag("USE_TOOLS", "false"):
        FrenchTutorPlus.set_level.livekit_tool = False
        FrenchTutorPlus.set_mode.livekit_tool = False
        FrenchTutorPlus.phrase_pack.livekit_tool = False
        FrenchTutorPlus.add_vocab.livekit_tool = False
        FrenchTutorPlus.list_vocab.livekit_tool = False
        FrenchTutorPlus.due_words.livekit_tool = False
        FrenchTutorPlus.start_quiz.livekit_tool = False
        FrenchTutorPlus.next_question.livekit_tool = False
        FrenchTutorPlus.answer_quiz.livekit_tool = False
        FrenchTutorPlus.give_sentence.livekit_tool = False
        FrenchTutorPlus.check_pronunciation.livekit_tool = False

    # 4) Audio stack
    _require_env(["DEEPGRAM_API_KEY", "OPENAI_TTS_API_KEY"])
    stt = deepgram.STT(model=_env("DEEPGRAM_MODEL", "nova-2"))
    tts = openai.TTS(voice=_env("TTS_VOICE", "alloy"), api_key=_env("OPENAI_TTS_API_KEY"))
    vad = silero.VAD.load()

    # 5) Start session
    session = AgentSession(stt=stt, llm=llm, tts=tts, vad=vad)
    await session.start(room=ctx.room, agent=FrenchTutorPlus())

    # Initial greeting and quick guidance
    await session.generate_reply(
        instructions=(
            "Greet warmly in Aussie English, then switch to French (A1 by default). "
            "Explain briefly that tools are available: set_level, set_mode, due_words, start_quiz, answer_quiz, give_sentence, check_pronunciation. "
            "If in 'quiz', call start_quiz(5,'en2fr') then wait for the user's answer and call answer_quiz with it. "
            "If in 'pronounce', call give_sentence(topic) then, after user repeats, call check_pronunciation with their line. "
            "Keep turns short and conversational."
        )
    )


# -------------------------
# Runner
# -------------------------
if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
