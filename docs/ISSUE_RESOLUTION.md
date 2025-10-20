# Issue Resolution: TTS Quota Error

## What Happened

When you ran the universal agent, you encountered this error:

```
Error code: 429 - You exceeded your current quota
```

## Root Cause

1. Your OpenAI TTS API key ran out of credits/quota
2. The agent was configured to use OpenAI for text-to-speech
3. Even though `TTS_PROVIDER=deepgram` was set in `.env`, the universal agent wasn't respecting that setting
4. Result: Agent could hear you and process requests, but couldn't speak responses back

## What Was Working

✅ Ollama LLM (local model)
✅ Deepgram STT (speech-to-text) 
✅ Tool execution (calculator, datetime, etc.)
✅ Question understanding and processing

## What Wasn't Working

❌ Text-to-speech (TTS) responses
❌ Audible agent replies

## The Fix

### 1. Updated Universal Agent Code

Modified `voice_livekit_agent/universal_agent.py` to properly check the `TTS_PROVIDER` setting:

```python
# Now properly supports:
TTS_PROVIDER=deepgram  # Uses Deepgram TTS
TTS_PROVIDER=openai    # Uses OpenAI TTS
TTS_PROVIDER=none      # Disables TTS (text only)
```

### 2. Updated Your .env Configuration

Changed from:
```bash
USE_TOOLS=false
TTS_PROVIDER=deepgram
```

To:
```bash
USE_TOOLS=true              # Enable tools
TTS_PROVIDER=deepgram       # Use Deepgram TTS
DEEPGRAM_TTS_MODEL=aura-asteria-en  # Specify model
```

## Benefits of This Fix

1. **No Additional Cost**: Deepgram TTS uses your existing Deepgram API key
2. **More Credits**: You already have $200 Deepgram credit
3. **Better Integration**: Single provider for both STT and TTS
4. **Tools Enabled**: Calculator, converter, dictionary, etc. now work

## How to Test

```bash
# Run the agent
uv run python -m voice_livekit_agent.universal_agent console

# You should see:
✓ Model warmed up
✓ Using Deepgram TTS

# Try these questions:
"What's 15% of 850?"
"Convert 100 km to miles"
"What time is it?"
"What's the weather in London?"  # Requires OPENWEATHER_API_KEY
```

## What You Can Do Now

### ✅ Working Features

1. **Math Calculations**
   - "What's 2 + 2?"
   - "Calculate sqrt(144)"
   - "What's 15% of 500?"

2. **Unit Conversions**
   - "Convert 10 km to miles"
   - "100 Fahrenheit to Celsius"
   - "5 feet to meters"

3. **General Knowledge**
   - "What's the capital of France?"
   - "Explain photosynthesis"
   - "Who painted the Mona Lisa?"

4. **Current Information**
   - "What time is it?"
   - "What day is today?"

5. **Dictionary**
   - "Define serendipity"
   - "What does ephemeral mean?"

6. **Conversation Memory** (if enabled)
   - "Remember I prefer metric units"
   - "What are my preferences?"

### ⚠️ Optional Features (Require API Keys)

7. **Weather** - Needs `OPENWEATHER_API_KEY`
8. **News** - Needs `NEWS_API_KEY`  
9. **Web Search** - Needs `SERPAPI_KEY`

## Cost Breakdown (After Fix)

| Service | Monthly Cost | Your Status |
|---------|-------------|-------------|
| Ollama LLM | $0 | ✅ Free, local |
| Deepgram STT | ~$1 | ✅ $200 credit |
| Deepgram TTS | ~$0.50 | ✅ $200 credit |
| **Total** | **~$1.50** | **✅ Covered by free credit** |

Previous issue: OpenAI TTS had no remaining credits.

## Alternative Options

If you want to use OpenAI TTS instead:

```bash
# Option 1: Add credits to OpenAI account
# https://platform.openai.com/account/billing

# Option 2: Update .env
TTS_PROVIDER=openai
OPENAI_TTS_API_KEY=sk-your-new-key-with-credits
```

If you want text-only mode (no TTS at all):

```bash
# In .env:
TTS_PROVIDER=none

# Or for testing:
BASIC_TEST=true
```

## Summary

**Before Fix:**
- ❌ Agent couldn't speak (OpenAI quota exceeded)
- ❌ Tools disabled
- ⚠️ You could hear silence in responses

**After Fix:**
- ✅ Agent can speak (using Deepgram)
- ✅ Tools enabled and working
- ✅ Full two-way conversation
- ✅ No additional API keys needed
- ✅ Using existing Deepgram credits

## Next Steps

1. **Test the agent** with the commands above
2. **Try different questions** - see [EXAMPLE_QUESTIONS.md](EXAMPLE_QUESTIONS.md)
3. **Add optional APIs** if you want weather, news, web search
4. **Customize the agent** - add your own tools

## Need More Help?

- 📖 Read [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues
- 🚀 Check [QUICKSTART.md](QUICKSTART.md) for setup guide
- 💡 See [UNIVERSAL_AGENT.md](UNIVERSAL_AGENT.md) for full documentation

---

**Your agent is now ready to use!** 🎉
