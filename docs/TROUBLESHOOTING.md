# Common Issues & Solutions

## Issue: TTS Quota Exceeded (OpenAI)

**Error Message:**
```
Error code: 429 - You exceeded your current quota, please check your plan and billing details.
```

**What happened:**
- Your OpenAI API key has run out of credits/quota
- The agent can hear you and process requests, but can't speak back

**Solution Options:**

### Option 1: Switch to Deepgram TTS (Recommended)

```bash
# Edit .env file
TTS_PROVIDER=deepgram
DEEPGRAM_TTS_MODEL=aura-asteria-en

# Deepgram uses the same API key as STT
# No additional key needed!
```

### Option 2: Disable TTS (Text Mode Only)

```bash
# Edit .env file
TTS_PROVIDER=none

# Agent will only show text responses
# You can still type or use STT
```

### Option 3: Add Credits to OpenAI Account

1. Go to https://platform.openai.com/account/billing
2. Add payment method and credits
3. Keep `TTS_PROVIDER=openai` in .env

### Option 4: Use Text Mode for Testing

```bash
# In .env, set:
BASIC_TEST=true

# Run without audio:
uv run python -m voice_livekit_agent.universal_agent console
```

## Issue: Agent Not Responding

**Symptoms:**
- Agent receives your messages
- Tools execute (you see DEBUG logs)
- No response appears

**Cause:** TTS is failing (see above)

**Quick Fix:**
```bash
# Switch to Deepgram TTS
TTS_PROVIDER=deepgram

# Or disable audio
TTS_PROVIDER=none
```

## Issue: "unknown sort specifier" Warning

**Message:**
```
zsh: unknown sort specifier
```

**Cause:** Shell interpretation issue with comments

**Solution:** Run commands without inline comments:
```bash
# Instead of:
uv run python -m voice_livekit_agent.universal_agent console # comment

# Do:
uv run python -m voice_livekit_agent.universal_agent console
```

## Issue: Tools Not Working

**Symptoms:**
- Agent responds but doesn't calculate, convert, etc.

**Solution:**
```bash
# In .env, make sure:
USE_TOOLS=true
```

## Issue: Ollama Connection Refused

**Error:**
```
Connection refused on port 11434
```

**Solution:**
```bash
# Start Ollama server in another terminal
ollama serve

# Verify it's running
curl http://localhost:11434/api/tags
```

## Issue: Model Not Found

**Error:**
```
Model 'llama3.2:3b' not found
```

**Solution:**
```bash
# Pull the model
ollama pull llama3.2:3b

# Verify
ollama list
```

## Issue: Agent Slow to Respond

**Causes & Solutions:**

### 1. First Response Slow
```bash
# In .env:
WARMUP_LLM=true
WARMUP_TIMEOUT=120  # Increase timeout
```

### 2. Model Too Large
```bash
# Use smaller model
LLM_MODEL=llama3.2:1b
```

### 3. Too Much Context
```bash
# Reduce conversation history
MAX_CONTEXT_TURNS=5
```

### 4. Temperature Too High
```bash
# Lower temperature for faster responses
LLM_TEMPERATURE=0.3
```

## Issue: Memory Not Persisting

**Symptoms:**
- Agent forgets preferences between sessions

**Solution:**
```bash
# In .env:
ENABLE_MEMORY=true
MEMORY_FILE=agent_memory.json

# Check file exists after conversation
ls -la agent_memory.json

# Check permissions
chmod 644 agent_memory.json
```

## Issue: Deepgram API Errors

**Error:**
```
Deepgram API error: 401 Unauthorized
```

**Solutions:**

### 1. Check API Key
```bash
# Verify key in .env
echo $DEEPGRAM_API_KEY

# Test API directly
curl -X POST https://api.deepgram.com/v1/listen \
  -H "Authorization: Token YOUR_KEY" \
  -H "Content-Type: audio/wav" \
  --data-binary @test.wav
```

### 2. Check Credits
- Go to https://console.deepgram.com/
- Check usage and remaining credits

### 3. Key Format
```bash
# Deepgram keys don't need 'Bearer' prefix
DEEPGRAM_API_KEY=your_key_here
# NOT: Bearer your_key_here
```

## Issue: "Web search unavailable"

**Message:**
```
Web search unavailable. To enable, set SERPAPI_KEY...
```

**This is normal!** Web search requires optional API key:
```bash
# To enable:
SERPAPI_KEY=your_serpapi_key

# Or ignore - other features still work
```

## Issue: High API Costs

**Solutions:**

### 1. Use Text Mode for Development
```bash
BASIC_TEST=true  # No STT/TTS costs
```

### 2. Switch to Deepgram TTS
```bash
TTS_PROVIDER=deepgram  # More affordable
```

### 3. Use Free Tiers
- Deepgram: $200 free credit
- OpenAI: $5 free credit
- Weather/News/Search: Free tiers available

### 4. Monitor Usage
```bash
# Check Deepgram usage
# https://console.deepgram.com/usage

# Check OpenAI usage
# https://platform.openai.com/usage
```

## Testing Your Setup

### Quick Health Check

```bash
# 1. Test Ollama
curl http://localhost:11434/api/tags

# 2. Test LLM only (no costs)
BASIC_TEST=true uv run python -m voice_livekit_agent.universal_agent console

# 3. Check .env file
cat .env | grep -E "(BASIC_TEST|USE_TOOLS|TTS_PROVIDER)"

# 4. Verify API keys (masks sensitive parts)
cat .env | grep -E "(API_KEY)" | sed 's/\(.\{10\}\).*/\1.../'
```

### Minimal Working Configuration

```bash
# For testing without API costs:
OPENAI_BASE_URL=http://127.0.0.1:11434/v1
OPENAI_API_KEY=ollama
LLM_MODEL=llama3.2:3b
BASIC_TEST=true
USE_TOOLS=true
```

### Full Voice Configuration

```bash
# For production with voice:
OPENAI_BASE_URL=http://127.0.0.1:11434/v1
OPENAI_API_KEY=ollama
LLM_MODEL=llama3.2:3b
BASIC_TEST=false
USE_TOOLS=true

# Use Deepgram for both STT and TTS
DEEPGRAM_API_KEY=your_deepgram_key
TTS_PROVIDER=deepgram
DEEPGRAM_TTS_MODEL=aura-asteria-en

# Optional features
ENABLE_MEMORY=true
OPENWEATHER_API_KEY=your_weather_key
```

## Getting Help

If you're still having issues:

1. **Check logs carefully** - Error messages usually indicate the problem
2. **Verify all API keys** - Make sure they're valid and have credits
3. **Test incrementally** - Start with BASIC_TEST=true, then add features
4. **Check GitHub issues** - Someone may have had the same problem
5. **Reduce complexity** - Disable optional features, use smaller model

## Debug Mode

```bash
# Enable verbose logging
export LOG_LEVEL=DEBUG

# Run with full output
uv run python -m voice_livekit_agent.universal_agent console 2>&1 | tee debug.log

# Check the log file
cat debug.log
```

## Still Not Working?

Try the absolute minimal setup:

```bash
# 1. Create fresh .env
cat > .env << 'EOF'
OPENAI_BASE_URL=http://127.0.0.1:11434/v1
OPENAI_API_KEY=ollama
LLM_MODEL=llama3.2:3b
BASIC_TEST=true
EOF

# 2. Make sure Ollama is running
ollama serve &

# 3. Pull model
ollama pull llama3.2:3b

# 4. Test
uv run python -m voice_livekit_agent.universal_agent console
```

If this works, gradually add features back one at a time.
