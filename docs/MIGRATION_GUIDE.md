# Migration Guide: Moving to Universal Agent

This guide helps you transition from the specialized agents to the new Universal Agent.

## Why Migrate?

The Universal Agent provides:
- ✅ **Broader capabilities**: Handle ANY question, not just specialized topics
- ✅ **Better reliability**: Comprehensive error handling
- ✅ **More features**: Built-in calculator, converter, dictionary, weather, news
- ✅ **Easier maintenance**: One agent instead of multiple
- ✅ **Better UX**: Clear error messages and guidance

## Quick Comparison

### Old: Basic Agent
```python
# Could only handle: Airbnb bookings, current time
# Tools: get_current_date_and_time, search_airbnbs, book_airbnb
```

### New: Universal Agent
```python
# Handles: Everything basic agent could + ALL other topics
# Tools: All basic tools + calculator, converter, dictionary, 
#        weather, news, web search, memory, and more
```

## Migration Steps

### Step 1: Update Dependencies

No changes needed! Universal Agent uses the same dependencies.

```bash
# Just make sure you're up to date
uv sync
```

### Step 2: Update .env File

```bash
# OLD .env
OPENAI_BASE_URL=http://127.0.0.1:11434/v1
OPENAI_API_KEY=ollama
LLM_MODEL=llama3.2:3b
BASIC_TEST=true
USE_TOOLS=false

# NEW .env (add these)
OPENAI_BASE_URL=http://127.0.0.1:11434/v1
OPENAI_API_KEY=ollama
LLM_MODEL=llama3.2:3b
BASIC_TEST=true
USE_TOOLS=true                    # Enable tools
ENABLE_MEMORY=true                # Enable conversation memory
MAX_CONTEXT_TURNS=10              # Remember 10 turns
MEMORY_FILE=agent_memory.json     # Where to store memory
```

### Step 3: Switch Your Command

```bash
# OLD: Running basic agent
uv run python -m voice_livekit_agent.livekit_basic_agent console

# NEW: Running universal agent
uv run python -m voice_livekit_agent.universal_agent console
```

That's it! 🎉

## Feature Mapping

### Basic Agent → Universal Agent

| Old Feature | New Feature | Notes |
|-------------|-------------|-------|
| `get_current_date_and_time()` | `get_current_datetime()` | Enhanced with more details |
| `search_airbnbs()` | Not included | Can be re-added as custom tool |
| `book_airbnb()` | Not included | Can be re-added as custom tool |
| - | `calculate()` | NEW: Math operations |
| - | `unit_converter()` | NEW: Convert units |
| - | `get_definition()` | NEW: Word definitions |
| - | `get_weather()` | NEW: Weather info |
| - | `search_news()` | NEW: News search |
| - | `remember_preference()` | NEW: Store user prefs |
| - | `explain_concept()` | NEW: Detailed explanations |

### French Tutor → Universal Agent + Custom Tools

The French Tutor functionality can be replicated:

```python
# Option 1: Keep using french_voice_tutor.py for French learning
# Option 2: Add French tools to universal_agent.py

# In universal_agent.py, add:
@function_tool
async def french_vocab(self, context: RunContext, word: str) -> str:
    """Get French translation and usage."""
    # Your French vocab logic here
    pass
```

## Custom Tool Migration

If you have custom tools in old agents:

### Old Pattern (Basic Agent)
```python
class Assistant(Agent):
    @function_tool
    async def my_custom_tool(self, context: RunContext, param: str) -> str:
        """My tool description."""
        return do_something(param)
```

### New Pattern (Universal Agent)
```python
class UniversalAgent(Agent):
    @function_tool
    async def my_custom_tool(
        self,
        context: RunContext,
        param: str
    ) -> str:
        """My tool description."""
        try:
            result = do_something(param)
            return f"Success: {result}"
        except Exception as e:
            return f"Error: {str(e)}"
```

**Key differences:**
1. Add try-except for error handling
2. Return user-friendly error messages
3. Keep tool names and signatures the same

## Configuration Changes

### Old .env (Minimal)
```bash
OPENAI_BASE_URL=http://127.0.0.1:11434/v1
OPENAI_API_KEY=ollama
LLM_MODEL=llama3.2:3b
BASIC_TEST=true
DEEPGRAM_API_KEY=xxx
OPENAI_TTS_API_KEY=xxx
```

### New .env (Enhanced)
```bash
# Core (same as before)
OPENAI_BASE_URL=http://127.0.0.1:11434/v1
OPENAI_API_KEY=ollama
LLM_MODEL=llama3.2:3b
BASIC_TEST=true

# Voice (same as before)
DEEPGRAM_API_KEY=xxx
OPENAI_TTS_API_KEY=xxx

# NEW: Features
USE_TOOLS=true
ENABLE_MEMORY=true
MEMORY_FILE=agent_memory.json
MAX_CONTEXT_TURNS=10

# NEW: Optional APIs
OPENWEATHER_API_KEY=xxx  # For weather
NEWS_API_KEY=xxx         # For news
SERPAPI_KEY=xxx          # For web search
```

## Behavior Changes

### 1. Error Handling

**Old behavior:**
```
User: "What's the weather?"
Agent: [crashes if no API key]
```

**New behavior:**
```
User: "What's the weather?"
Agent: "Weather service unavailable. To enable, set OPENWEATHER_API_KEY..."
```

### 2. Tool Availability

**Old behavior:**
- All tools always available
- Could fail silently

**New behavior:**
- Tools auto-enable based on API keys
- Clear messages when unavailable
- Suggests alternatives

### 3. Conversation Context

**Old behavior:**
```
User: "Remember I prefer metric"
Agent: "Okay" [forgets after session]
```

**New behavior:**
```
User: "Remember I prefer metric"
Agent: "I'll remember that: units = metric"
[Persists across sessions when ENABLE_MEMORY=true]
```

## Testing After Migration

### 1. Basic Smoke Test
```bash
# Should work immediately
BASIC_TEST=true uv run python -m voice_livekit_agent.universal_agent console
```

### 2. Test Core Tools
```bash
# Update .env: USE_TOOLS=true, BASIC_TEST=false
uv run python -m voice_livekit_agent.universal_agent console

# Try:
"What's 2 + 2?"          # Calculator
"Convert 10 km to mi"    # Unit converter
"Define serendipity"     # Dictionary
"What time is it?"       # DateTime
```

### 3. Test Memory (if enabled)
```bash
# Session 1
You: "Remember I'm learning Python"
Agent: "I'll remember that..."

# Exit and restart

# Session 2
You: "What are my preferences?"
Agent: "Your preferences: learning = Python"
```

### 4. Test Optional Features
```bash
# Requires API keys in .env
"What's the weather in Tokyo?"    # OPENWEATHER_API_KEY
"Latest AI news"                  # NEWS_API_KEY
"Search for Python tutorials"     # SERPAPI_KEY
```

## Rollback Plan

If you need to rollback:

```bash
# Option 1: Keep using old agents
uv run python -m voice_livekit_agent.livekit_basic_agent console
uv run python -m voice_livekit_agent.french_voice_tutor console

# Option 2: Both agents coexist
# You can run both simultaneously!
```

## Common Issues

### "Tools not working"
```bash
# Solution: Enable tools in .env
USE_TOOLS=true
```

### "Memory not persisting"
```bash
# Solution: Enable memory and check file permissions
ENABLE_MEMORY=true
MEMORY_FILE=agent_memory.json

# Check file exists after first conversation
ls -la agent_memory.json
```

### "Weather/News unavailable"
```bash
# Expected: These are optional
# Add API keys to .env to enable:
OPENWEATHER_API_KEY=your_key
NEWS_API_KEY=your_key
```

### "Agent slower than before"
```bash
# Universal agent has more features
# For faster responses:
LLM_MODEL=llama3.2:1b      # Use smaller model
LLM_TEMPERATURE=0.3        # Lower temperature
MAX_CONTEXT_TURNS=5        # Reduce context window
```

## Performance Comparison

| Metric | Old Agents | Universal Agent |
|--------|-----------|-----------------|
| Startup time | ~2s | ~3s (warmup) |
| Response time | ~1-2s | ~1-3s (more processing) |
| Memory usage | ~500MB | ~600MB (memory system) |
| API calls | Only when used | Same |
| Error rate | Higher (no handling) | Lower (graceful) |

## FAQ

**Q: Can I still use the old agents?**
A: Yes! All old agents still work. Universal Agent is an addition, not a replacement.

**Q: Do I need to migrate?**
A: No, but recommended for better reliability and features.

**Q: Can I customize Universal Agent?**
A: Absolutely! It's designed to be extended. See docs/UNIVERSAL_AGENT.md

**Q: Will my API keys work?**
A: Yes! Same APIs, same keys.

**Q: What about French Tutor features?**
A: French Tutor still works as-is. Universal Agent focuses on general knowledge.

**Q: Is Universal Agent slower?**
A: Slightly (~0.5-1s) due to more features, but you can optimize (see above).

**Q: Can I add my old custom tools?**
A: Yes! Just copy them to universal_agent.py with error handling.

## Next Steps

1. ✅ Update .env with new settings
2. ✅ Test with BASIC_TEST=true
3. ✅ Try example questions
4. ✅ Enable optional features
5. ✅ Add your custom tools
6. ✅ Deploy to production

## Need Help?

- 📖 Full docs: `docs/UNIVERSAL_AGENT.md`
- 🚀 Quick start: `docs/QUICKSTART.md`
- 💡 Examples: `docs/EXAMPLE_QUESTIONS.md`
- 🐛 Issues: Open a GitHub issue

---

**Happy migrating! 🚀**
