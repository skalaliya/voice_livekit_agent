"""
Universal Voice Agent - Robust & Versatile (LiveKit + Ollama + Deepgram + OpenAI TTS)
------------------------------------------------------------------------------------
A comprehensive voice agent that can handle ANY type of question with:
  • Robust error handling and graceful degradation
  • Dynamic tool registration based on available API keys
  • Conversation memory and context tracking
  • Multiple knowledge domains (general, tech, travel, education, finance, etc.)
  • Web search capabilities (when available)
  • Code execution and analysis
  • File operations and data processing

Environment Variables:
  Core LLM (Required):
    OPENAI_BASE_URL=http://127.0.0.1:11434/v1
    OPENAI_API_KEY=ollama
    LLM_MODEL=llama3.2:3b
    LLM_TEMPERATURE=0.7
    
  Testing Mode:
    BASIC_TEST=true          # Run smoke test and exit
    WARMUP_LLM=true          # Warm up model on startup
    WARMUP_TIMEOUT=60
    
  Voice Mode (when BASIC_TEST=false):
    DEEPGRAM_API_KEY=...     # For speech-to-text
    OPENAI_TTS_API_KEY=...   # For text-to-speech
    TTS_VOICE=alloy          # TTS voice selection
    DEEPGRAM_MODEL=nova-2    # STT model
    
  Advanced Features:
    USE_TOOLS=true           # Enable function tools
    ENABLE_WEB_SEARCH=false  # Enable web search (requires API)
    ENABLE_CODE_EXEC=false   # Enable code execution (sandbox)
    MAX_CONTEXT_TURNS=10     # Conversation history limit
    ENABLE_MEMORY=true       # Persistent conversation memory
    MEMORY_FILE=agent_memory.json
    
  API Keys (Optional):
    OPENWEATHER_API_KEY=...  # For weather queries
    NEWS_API_KEY=...         # For news queries
    SERPAPI_KEY=...          # For web search
    
Run:
  uv run python -m voice_livekit_agent.universal_agent console
"""

from __future__ import annotations

import json
import os
import re
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import quote

import requests
from dotenv import load_dotenv

from livekit import agents
from livekit.agents import Agent, AgentSession, RunContext, io
from livekit.agents.llm import function_tool
from livekit.plugins import deepgram, openai, silero

# Load environment variables
load_dotenv(".env")


# -------------------------
# Utility Functions
# -------------------------
def _flag(name: str, default: str = "false") -> bool:
    """Check if an environment variable is set to true."""
    return (os.getenv(name, default) or "").strip().lower() in {"1", "true", "yes", "on"}


def _env(key: str, default: str | None = None) -> str | None:
    """Get environment variable with default."""
    return os.getenv(key, default)


def _require_env(keys: List[str]) -> None:
    """Ensure required environment variables are set."""
    missing = [k for k in keys if not os.getenv(k)]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            "Tip: add them to your .env (do NOT commit secrets)."
        )


def safe_json_loads(text: str, default: Any = None) -> Any:
    """Safely parse JSON with fallback."""
    try:
        return json.loads(text)
    except Exception:
        return default


def safe_request(
    url: str,
    method: str = "GET",
    timeout: int = 5,
    **kwargs
) -> Optional[requests.Response]:
    """Make HTTP request with error handling."""
    try:
        response = requests.request(method, url, timeout=timeout, **kwargs)
        response.raise_for_status()
        return response
    except requests.exceptions.Timeout:
        print(f"Request timeout for {url}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request error for {url}: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None


# -------------------------
# Conversation Memory System
# -------------------------
class ConversationMemory:
    """Persistent conversation memory with context tracking."""
    
    def __init__(self, memory_file: str = "agent_memory.json", max_turns: int = 10):
        self.memory_file = Path(memory_file)
        self.max_turns = max_turns
        self.conversations: List[Dict[str, Any]] = []
        self.user_preferences: Dict[str, Any] = {}
        self.facts_learned: List[Dict[str, Any]] = []
        self._load()
    
    def _load(self):
        """Load memory from disk."""
        try:
            if self.memory_file.exists():
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.conversations = data.get('conversations', [])[-self.max_turns:]
                    self.user_preferences = data.get('user_preferences', {})
                    self.facts_learned = data.get('facts_learned', [])
        except Exception as e:
            print(f"Memory load error: {e}")
    
    def _save(self):
        """Save memory to disk."""
        try:
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'conversations': self.conversations[-self.max_turns:],
                    'user_preferences': self.user_preferences,
                    'facts_learned': self.facts_learned,
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Memory save error: {e}")
    
    def add_turn(self, user_msg: str, agent_msg: str, metadata: Optional[Dict] = None):
        """Add a conversation turn."""
        self.conversations.append({
            'timestamp': datetime.now().isoformat(),
            'user': user_msg,
            'agent': agent_msg,
            'metadata': metadata or {}
        })
        self._save()
    
    def add_preference(self, key: str, value: Any):
        """Remember user preference."""
        self.user_preferences[key] = value
        self._save()
    
    def add_fact(self, fact: str, category: str = "general"):
        """Remember a learned fact."""
        self.facts_learned.append({
            'fact': fact,
            'category': category,
            'learned_at': datetime.now().isoformat()
        })
        self._save()
    
    def get_context_summary(self) -> str:
        """Get a summary of recent context."""
        if not self.conversations:
            return "No previous conversation history."
        
        summary = ["Recent conversation context:"]
        for turn in self.conversations[-3:]:
            summary.append(f"User: {turn['user'][:100]}...")
            summary.append(f"Agent: {turn['agent'][:100]}...")
        
        if self.user_preferences:
            summary.append(f"\nUser preferences: {self.user_preferences}")
        
        return "\n".join(summary)


# -------------------------
# Universal Agent
# -------------------------
class UniversalAgent(Agent):
    """
    A robust, versatile voice agent that can handle any type of question.
    """
    
    def __init__(self):
        super().__init__(
            instructions=(
                "You are an incredibly helpful, knowledgeable, and friendly AI assistant. "
                "You can answer questions on ANY topic including: "
                "general knowledge, science, technology, mathematics, history, geography, "
                "literature, arts, entertainment, sports, health, finance, cooking, travel, "
                "education, business, programming, and more. "
                "\n\n"
                "IMPORTANT GUIDELINES:\n"
                "- Respond naturally to greetings (Hey, Hello, Can you hear me?) WITHOUT using tools\n"
                "- Always try to help, even if you're not 100% certain\n"
                "- If you don't know something, say so clearly and suggest alternatives\n"
                "- Break down complex topics into simple, understandable explanations\n"
                "- Use examples and analogies to clarify concepts\n"
                "- Be conversational and engaging\n"
                "- Keep responses concise (1-3 sentences for simple questions)\n"
                "- Remember context from previous messages\n"
                "- Admit mistakes and correct them gracefully\n"
                "- For ambiguous questions, ask clarifying questions\n"
                "- Prioritize accuracy over speed\n"
                "\n"
                "When using tools:\n"
                "- ONLY use tools when clearly needed (calculations, conversions, definitions, etc.)\n"
                "- Do NOT use get_definition for casual conversation or greetings\n"
                "- If a tool fails, explain the issue and try alternative approaches\n"
                "- Combine multiple tools when needed for comprehensive answers\n"
            )
        )
        
        # Initialize conversation memory
        self.memory = ConversationMemory(
            memory_file=_env("MEMORY_FILE", "agent_memory.json"),
            max_turns=int(_env("MAX_CONTEXT_TURNS", "10"))
        ) if _flag("ENABLE_MEMORY", "true") else None
        
        # Feature flags
        self.web_search_enabled = _flag("ENABLE_WEB_SEARCH", "false")
        self.code_exec_enabled = _flag("ENABLE_CODE_EXEC", "false")
        
        # API availability
        self.has_weather_api = bool(_env("OPENWEATHER_API_KEY"))
        self.has_news_api = bool(_env("NEWS_API_KEY"))
        self.has_search_api = bool(_env("SERPAPI_KEY"))
        
        # Knowledge cache
        self.knowledge_cache: Dict[str, Any] = {}
    
    # -------------------------
    # Core Utility Tools
    # -------------------------
    
    @function_tool
    async def get_current_datetime(self, context: RunContext) -> str:
        """Get the current date, time, day of week, and timezone information."""
        try:
            now = datetime.now()
            return (
                f"Current date and time: {now.strftime('%A, %B %d, %Y at %I:%M:%S %p')} "
                f"(24h format: {now.strftime('%H:%M:%S')})"
            )
        except Exception as e:
            return f"Error getting time: {str(e)}"
    
    @function_tool
    async def calculate(
        self,
        context: RunContext,
        expression: str,
        description: Optional[str] = None
    ) -> str:
        """
        Perform mathematical calculations safely.
        Use this ONLY for actual math calculations, percentages, formulas.
        Examples: "What's 2 + 2?", "Calculate sqrt(16)", "15% of 200"
        Do NOT use for greetings or non-mathematical questions.
        """
        try:
            # Safe eval with limited math functions
            import math
            safe_dict = {
                'sqrt': math.sqrt,
                'sin': math.sin,
                'cos': math.cos,
                'tan': math.tan,
                'log': math.log,
                'log10': math.log10,
                'exp': math.exp,
                'pi': math.pi,
                'e': math.e,
                'abs': abs,
                'round': round,
                'pow': pow,
            }
            
            # Remove any potentially dangerous operations
            if any(word in expression.lower() for word in ['import', 'exec', 'eval', '__']):
                return "Error: Expression contains unsafe operations"
            
            result = eval(expression, {"__builtins__": {}}, safe_dict)
            desc = f" ({description})" if description else ""
            return f"Result{desc}: {result}"
        except Exception as e:
            return f"Calculation error: {str(e)}"
    
    @function_tool
    async def unit_converter(
        self,
        context: RunContext,
        value: float,
        from_unit: str,
        to_unit: str
    ) -> str:
        """
        Convert between common units.
        Supported: length (m, km, mi, ft, in), weight (kg, lb, oz, g),
        temperature (C, F, K), volume (L, gal, ml, cup)
        """
        try:
            conversions = {
                # Length (to meters)
                'm': 1, 'km': 1000, 'mi': 1609.34, 'ft': 0.3048, 'in': 0.0254,
                'cm': 0.01, 'mm': 0.001,
                # Weight (to kg)
                'kg': 1, 'g': 0.001, 'lb': 0.453592, 'oz': 0.0283495,
                # Volume (to liters)
                'L': 1, 'ml': 0.001, 'gal': 3.78541, 'cup': 0.236588,
            }
            
            from_u = from_unit.lower()
            to_u = to_unit.lower()
            
            # Temperature conversions (special case)
            if from_u in ['c', 'f', 'k'] or to_u in ['c', 'f', 'k']:
                if from_u == 'c' and to_u == 'f':
                    result = value * 9/5 + 32
                elif from_u == 'f' and to_u == 'c':
                    result = (value - 32) * 5/9
                elif from_u == 'c' and to_u == 'k':
                    result = value + 273.15
                elif from_u == 'k' and to_u == 'c':
                    result = value - 273.15
                elif from_u == 'f' and to_u == 'k':
                    result = (value - 32) * 5/9 + 273.15
                elif from_u == 'k' and to_u == 'f':
                    result = (value - 273.15) * 9/5 + 32
                else:
                    return f"Cannot convert {from_unit} to {to_unit}"
                return f"{value} {from_unit} = {result:.2f} {to_unit}"
            
            # Other conversions
            if from_u in conversions and to_u in conversions:
                # Check if same category (rough check)
                base_value = value * conversions[from_u]
                result = base_value / conversions[to_u]
                return f"{value} {from_unit} = {result:.4f} {to_unit}"
            
            return f"Cannot convert {from_unit} to {to_unit}"
        except Exception as e:
            return f"Conversion error: {str(e)}"
    
    @function_tool
    async def get_weather(
        self,
        context: RunContext,
        location: str,
        units: str = "metric"
    ) -> str:
        """
        Get current weather for a location.
        Units: metric (°C) or imperial (°F)
        """
        api_key = _env("OPENWEATHER_API_KEY")
        if not api_key:
            return (
                "Weather service unavailable. "
                "To enable, set OPENWEATHER_API_KEY in your .env file. "
                "Get a free API key at https://openweathermap.org/api"
            )
        
        try:
            url = f"http://api.openweathermap.org/data/2.5/weather"
            params = {
                'q': location,
                'appid': api_key,
                'units': units
            }
            
            response = safe_request(url, params=params)
            if not response:
                return f"Could not fetch weather data for {location}"
            
            data = response.json()
            temp_unit = "°C" if units == "metric" else "°F"
            
            weather = data['weather'][0]['description']
            temp = data['main']['temp']
            feels_like = data['main']['feels_like']
            humidity = data['main']['humidity']
            wind_speed = data['wind']['speed']
            
            return (
                f"Weather in {location}:\n"
                f"• Conditions: {weather.capitalize()}\n"
                f"• Temperature: {temp}{temp_unit} (feels like {feels_like}{temp_unit})\n"
                f"• Humidity: {humidity}%\n"
                f"• Wind speed: {wind_speed} {'m/s' if units == 'metric' else 'mph'}"
            )
        except Exception as e:
            return f"Weather lookup error: {str(e)}"
    
    @function_tool
    async def search_news(
        self,
        context: RunContext,
        query: str,
        limit: int = 5
    ) -> str:
        """Search for recent news articles on a topic."""
        api_key = _env("NEWS_API_KEY")
        if not api_key:
            return (
                "News service unavailable. "
                "To enable, set NEWS_API_KEY in your .env file. "
                "Get a free API key at https://newsapi.org/"
            )
        
        try:
            url = "https://newsapi.org/v2/everything"
            params = {
                'q': query,
                'apiKey': api_key,
                'sortBy': 'publishedAt',
                'language': 'en',
                'pageSize': limit
            }
            
            response = safe_request(url, params=params)
            if not response:
                return f"Could not fetch news for: {query}"
            
            data = response.json()
            articles = data.get('articles', [])
            
            if not articles:
                return f"No recent news found for: {query}"
            
            results = [f"Latest news about '{query}':\n"]
            for i, article in enumerate(articles, 1):
                title = article.get('title', 'No title')
                source = article.get('source', {}).get('name', 'Unknown')
                published = article.get('publishedAt', '')[:10]
                url = article.get('url', '')
                results.append(f"{i}. {title}")
                results.append(f"   Source: {source} ({published})")
            
            return "\n".join(results)
        except Exception as e:
            return f"News search error: {str(e)}"
    
    @function_tool
    async def web_search(
        self,
        context: RunContext,
        query: str,
        num_results: int = 3
    ) -> str:
        """
        Search the web for information.
        Returns titles and snippets from search results.
        """
        if not self.has_search_api:
            return (
                "Web search unavailable. "
                "To enable, set SERPAPI_KEY in your .env file. "
                "Get a free API key at https://serpapi.com/"
            )
        
        try:
            api_key = _env("SERPAPI_KEY")
            url = "https://serpapi.com/search"
            params = {
                'q': query,
                'api_key': api_key,
                'num': num_results
            }
            
            response = safe_request(url, params=params)
            if not response:
                return f"Web search failed for: {query}"
            
            data = response.json()
            results = data.get('organic_results', [])
            
            if not results:
                return f"No web results found for: {query}"
            
            output = [f"Web search results for '{query}':\n"]
            for i, result in enumerate(results[:num_results], 1):
                title = result.get('title', 'No title')
                snippet = result.get('snippet', 'No description')
                output.append(f"{i}. {title}")
                output.append(f"   {snippet}\n")
            
            return "\n".join(output)
        except Exception as e:
            return f"Web search error: {str(e)}"
    
    @function_tool
    async def remember_preference(
        self,
        context: RunContext,
        key: str,
        value: str
    ) -> str:
        """Remember a user preference or fact for future conversations."""
        if not self.memory:
            return "Memory is disabled. Enable with ENABLE_MEMORY=true"
        
        try:
            self.memory.add_preference(key, value)
            return f"I'll remember that: {key} = {value}"
        except Exception as e:
            return f"Memory error: {str(e)}"
    
    @function_tool
    async def recall_preferences(self, context: RunContext) -> str:
        """Recall all stored user preferences."""
        if not self.memory:
            return "Memory is disabled."
        
        if not self.memory.user_preferences:
            return "I don't have any preferences stored yet."
        
        prefs = [f"Your preferences:"]
        for key, value in self.memory.user_preferences.items():
            prefs.append(f"• {key}: {value}")
        
        return "\n".join(prefs)
    
    @function_tool
    async def get_definition(
        self,
        context: RunContext,
        word: str
    ) -> str:
        """
        Get the definition of a word using a free dictionary API.
        Only use this when the user explicitly asks for a definition (e.g., "define X", "what does X mean").
        Do NOT use for greetings or casual conversation.
        """
        try:
            url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
            response = safe_request(url, timeout=5)
            
            if not response:
                return f"Could not find definition for: {word}"
            
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                entry = data[0]
                word_text = entry.get('word', word)
                phonetic = entry.get('phonetic', '')
                meanings = entry.get('meanings', [])
                
                result = [f"Definition of '{word_text}' {phonetic}:\n"]
                
                for meaning in meanings[:2]:  # Limit to 2 meanings
                    part_of_speech = meaning.get('partOfSpeech', '')
                    definitions = meaning.get('definitions', [])
                    
                    if definitions:
                        result.append(f"As a {part_of_speech}:")
                        for i, defn in enumerate(definitions[:2], 1):
                            definition = defn.get('definition', '')
                            example = defn.get('example', '')
                            result.append(f"  {i}. {definition}")
                            if example:
                                result.append(f"     Example: \"{example}\"")
                
                return "\n".join(result)
            
            return f"No definition found for: {word}"
        except Exception as e:
            return f"Definition lookup error: {str(e)}"
    
    @function_tool
    async def explain_concept(
        self,
        context: RunContext,
        concept: str,
        detail_level: str = "medium"
    ) -> str:
        """
        Explain a concept at different detail levels.
        detail_level: "simple" (ELI5), "medium" (standard), "detailed" (in-depth)
        """
        level_instructions = {
            "simple": "Explain like I'm 5 years old, using simple words and fun analogies.",
            "medium": "Provide a clear, balanced explanation suitable for general audiences.",
            "detailed": "Give an in-depth, comprehensive explanation with technical details."
        }
        
        instruction = level_instructions.get(detail_level, level_instructions["medium"])
        
        return (
            f"[Agent will explain '{concept}' at {detail_level} level. "
            f"Instruction: {instruction}]"
        )
    
    # -------------------------
    # Advanced Tools (when enabled)
    # -------------------------
    
    @function_tool
    async def execute_python_code(
        self,
        context: RunContext,
        code: str,
        description: Optional[str] = None
    ) -> str:
        """
        Execute Python code safely in a restricted environment.
        Only available when ENABLE_CODE_EXEC=true
        """
        if not self.code_exec_enabled:
            return (
                "Code execution is disabled. "
                "To enable, set ENABLE_CODE_EXEC=true in your .env file."
            )
        
        try:
            # Create a restricted execution environment
            safe_globals = {
                '__builtins__': {
                    'print': print,
                    'len': len,
                    'range': range,
                    'str': str,
                    'int': int,
                    'float': float,
                    'list': list,
                    'dict': dict,
                    'tuple': tuple,
                    'set': set,
                    'abs': abs,
                    'max': max,
                    'min': min,
                    'sum': sum,
                    'sorted': sorted,
                }
            }
            
            # Execute code
            exec(code, safe_globals)
            
            desc_text = f" ({description})" if description else ""
            return f"Code executed successfully{desc_text}"
        except Exception as e:
            return f"Code execution error: {str(e)}"
    
    # -------------------------
    # Session Handlers
    # -------------------------
    
    async def handle_user_message(self, message: str) -> str:
        """Process user message with context."""
        if self.memory:
            # Add to conversation history (will be filled by session)
            self.memory.add_turn(message, "", {})
        
        return message
    
    async def handle_agent_response(self, response: str) -> str:
        """Process agent response before sending."""
        if self.memory and self.memory.conversations:
            # Update the last conversation turn with agent response
            last_turn = self.memory.conversations[-1]
            last_turn['agent'] = response
            self.memory._save()
        
        return response


# -------------------------
# LLM Smoke Test
# -------------------------
def _basic_llm_check() -> None:
    """Test LLM connectivity without audio."""
    base = _env("OPENAI_BASE_URL", "http://127.0.0.1:11434/v1")
    api = _env("OPENAI_API_KEY", "ollama")
    model = _env("LLM_CHOICE") or _env("LLM_MODEL", "llama3.2:3b")
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "user", "content": "Say 'System operational' in one sentence."},
        ],
    }
    
    try:
        r = requests.post(
            f"{base}/chat/completions",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api}"},
            json=payload,
            timeout=60,
        )
        r.raise_for_status()
        msg = r.json()["choices"][0]["message"]["content"]
        print(f"✓ LLM CHECK OK (model={model}, base={base})")
        print(f"  Response: {msg}")
    except Exception as e:
        print(f"✗ LLM CHECK FAILED: {e}")
        raise


def _warmup_ollama():
    """Warm up Ollama to avoid first-token timeout."""
    base = _env("OPENAI_BASE_URL", "http://127.0.0.1:11434/v1")
    api = _env("OPENAI_API_KEY", "ollama")
    model = _env("LLM_CHOICE") or _env("LLM_MODEL", "llama3.2:3b")
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are ready."},
            {"role": "user", "content": "Confirm ready."}
        ],
    }
    
    try:
        requests.post(
            f"{base}/chat/completions",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api}"},
            json=payload,
            timeout=float(_env("WARMUP_TIMEOUT", "60")),
        )
        print("✓ Model warmed up")
    except Exception as e:
        print(f"⚠ Warmup warning: {e}")


# -------------------------
# Console Output Sink
# -------------------------
class ConsoleTextSink(io.TextOutput):
    """Mirror agent replies to terminal."""
    
    def __init__(self, *, label: str = "console_logger", next_in_chain: io.TextOutput | None = None):
        super().__init__(label=label, next_in_chain=next_in_chain)
        self._buffer: list[str] = []
    
    async def capture_text(self, text: str) -> None:
        self._buffer.append(text)
        print(f"[Agent] {text}", end="", flush=True)
        if self.next_in_chain:
            await self.next_in_chain.capture_text(text)
    
    def flush(self) -> None:
        if self._buffer:
            print()
            self._buffer.clear()
        if self.next_in_chain:
            self.next_in_chain.flush()


# -------------------------
# LiveKit Entrypoint
# -------------------------
async def entrypoint(ctx: agents.JobContext):
    """Main entry point for the universal agent."""
    
    # 1) Basic test mode
    if _flag("BASIC_TEST", "true"):
        _basic_llm_check()
        return
    
    # 2) Warm up model
    if _flag("WARMUP_LLM", "true"):
        _warmup_ollama()
    
    # 3) Initialize LLM
    llm = openai.LLM(
        model=_env("LLM_CHOICE") or _env("LLM_MODEL", "llama3.2:3b"),
        base_url=_env("OPENAI_BASE_URL", "http://127.0.0.1:11434/v1"),
        api_key=_env("OPENAI_API_KEY", "ollama"),
        temperature=float(_env("LLM_TEMPERATURE", "0.7")),
    )
    
    # 4) Conditionally enable tools
    if not _flag("USE_TOOLS", "true"):
        # Disable all tools if not explicitly enabled
        for attr_name in dir(UniversalAgent):
            attr = getattr(UniversalAgent, attr_name)
            if callable(attr) and hasattr(attr, '__livekit_tool_info'):
                setattr(attr, 'livekit_tool', False)
    
    # 5) Setup audio pipeline
    try:
        _require_env(["DEEPGRAM_API_KEY"])
        stt = deepgram.STT(model=_env("DEEPGRAM_MODEL", "nova-2"))
    except RuntimeError:
        print("⚠ Deepgram API key not found. STT disabled.")
        stt = None
    
    # Setup TTS based on provider
    tts_provider = (_env("TTS_PROVIDER", "openai") or "openai").strip().lower()
    tts = None
    
    if tts_provider == "deepgram":
        try:
            _require_env(["DEEPGRAM_API_KEY"])
            tts = deepgram.TTS(
                model=_env("DEEPGRAM_TTS_MODEL", "aura-asteria-en"),
                api_key=_env("DEEPGRAM_API_KEY"),
            )
            print(f"✓ Using Deepgram TTS")
        except RuntimeError:
            print("⚠ Deepgram TTS: API key not found. TTS disabled.")
    elif tts_provider in {"none", "off", "disabled"}:
        print("ℹ TTS disabled by configuration")
        tts = None
    else:
        # Default to OpenAI TTS
        try:
            _require_env(["OPENAI_TTS_API_KEY"])
            tts_base_url = _env("OPENAI_TTS_BASE_URL", "https://api.openai.com/v1")
            tts = openai.TTS(
                voice=_env("TTS_VOICE", "alloy"),
                api_key=_env("OPENAI_TTS_API_KEY"),
                base_url=tts_base_url,
            )
            print(f"✓ Using OpenAI TTS")
        except RuntimeError:
            print("⚠ OpenAI TTS API key not found. TTS disabled.")
    
    vad = silero.VAD.load()
    
    # 6) Create and start session
    session = AgentSession(
        stt=stt,
        llm=llm,
        tts=tts,
        vad=vad,
    )
    
    # Add console output
    existing_transcript_sink = session.output.transcription
    session.output.transcription = ConsoleTextSink(next_in_chain=existing_transcript_sink)
    
    # Initialize agent
    agent = UniversalAgent()
    
    await session.start(room=ctx.room, agent=agent)
    
    # Initial greeting
    context_info = agent.memory.get_context_summary() if agent.memory else ""
    greeting_instructions = (
        "Greet the user very briefly and naturally in 1-2 sentences. "
        "Say hello and mention you can help with any questions they have. "
        "Be warm and conversational. Don't list features or tools. "
        f"{context_info}"
    )
    
    await session.generate_reply(instructions=greeting_instructions)


# -------------------------
# Runner
# -------------------------
if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
