# Quick Start Guide - Universal Agent

Get your robust AI assistant running in **5 minutes**! 🚀

## Prerequisites

- **Python 3.9+** installed
- **10 minutes** and a terminal
- **No API keys needed** for basic testing

## Step 1: Install Ollama (2 minutes)

### macOS
```bash
brew install ollama
```

### Linux
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Windows
Download from https://ollama.com/download

## Step 2: Start Ollama & Pull Model (3 minutes)

```bash
# Start Ollama server (keep this terminal open)
ollama serve

# In a NEW terminal, pull the model
ollama pull llama3.2:3b

# Verify it's working
ollama run llama3.2:3b "Say hello"
```

## Step 3: Setup Project (1 minute)

```bash
# Clone the repo (or download ZIP)
cd voice_livekit_agent

# Install dependencies
uv sync
# OR: pip install -e .

# Copy environment config
cp .env.example .env
```

## Step 4: Test It! (30 seconds)

```bash
# Run basic LLM test (no audio, no API keys needed)
uv run python -m voice_livekit_agent.universal_agent console
```

You should see:
```
✓ LLM CHECK OK (model=llama3.2:3b, ...)
  Response: System operational
```

✅ **Success!** Your agent is working!

## Step 5: Try Text-Based Conversations

```bash
# Edit .env: Keep BASIC_TEST=true but enable tools
USE_TOOLS=true

# Run the agent
uv run python -m voice_livekit_agent.universal_agent console
```

Now you can type questions:
```
You: What's 25% of 400?
Agent: [Calculating...] Result: 100

You: Convert 10 miles to kilometers
Agent: 10 mi = 16.09 km

You: What's the capital of France?
Agent: The capital of France is Paris...
```

Press `Ctrl+C` to exit.

## Step 6: Enable Voice (Optional)

### Get Free API Keys

1. **Deepgram STT** (Speech-to-Text)
   - Visit: https://console.deepgram.com/signup
   - Get $200 free credit
   - Copy your API key

2. **OpenAI TTS** (Text-to-Speech)
   - Visit: https://platform.openai.com/signup
   - Get $5 free credit
   - Copy your API key

### Update Configuration

```bash
# Edit .env file
BASIC_TEST=false
DEEPGRAM_API_KEY=your_deepgram_key_here
OPENAI_TTS_API_KEY=your_openai_key_here
USE_TOOLS=true
```

### Run with Voice

```bash
uv run python -m voice_livekit_agent.universal_agent console

# Grant microphone access if prompted
# Press Ctrl+B to toggle between audio and text
```

🎉 **You're talking to your AI!**

## Common Questions

### "Model not found" error?
```bash
# Make sure you pulled the model
ollama pull llama3.2:3b

# List available models
ollama list
```

### "Connection refused" on port 11434?
```bash
# Start Ollama in another terminal
ollama serve
```

### Agent responds slowly?
```bash
# Try a smaller model
ollama pull llama3.2:1b

# Update .env
LLM_MODEL=llama3.2:1b
```

### Want better quality?
```bash
# Try a larger model (needs more RAM)
ollama pull llama3:8b

# Update .env
LLM_MODEL=llama3:8b
```

## Next Steps

### 1. Enable More Features

```bash
# Add to .env for advanced features:
ENABLE_MEMORY=true              # Remembers conversations
OPENWEATHER_API_KEY=xxx         # Get weather info
NEWS_API_KEY=xxx                # Search news
SERPAPI_KEY=xxx                 # Web search
```

### 2. Try Example Questions

See [EXAMPLE_QUESTIONS.md](EXAMPLE_QUESTIONS.md) for 100+ example questions across all topics.

### 3. Customize the Agent

Edit `voice_livekit_agent/universal_agent.py` to:
- Add your own tools
- Change personality/instructions
- Integrate with your APIs
- Add new knowledge domains

### 4. Deploy to Production

```bash
# Build for production
uv build

# Run as a service
systemctl start voice-agent
```

## Troubleshooting

### Check Everything is Working

```bash
# Test Ollama
curl http://localhost:11434/api/tags

# Test Python environment
python --version

# Test dependencies
uv run python -c "import livekit; print('OK')"

# Run full diagnostic
uv run python scripts/smoke_test.py
```

### Still Having Issues?

1. Check logs: Look for error messages in terminal
2. Verify API keys: Make sure they're valid and have credits
3. Test network: Ensure you can reach APIs
4. Check permissions: Grant microphone access on macOS/Windows

### Get Help

- 📖 Read full docs: [UNIVERSAL_AGENT.md](UNIVERSAL_AGENT.md)
- 🐛 Report bugs: Open a GitHub issue
- 💬 Ask questions: Check discussions on GitHub

## What You've Built 🎯

You now have a **production-ready AI assistant** that can:

✅ Answer questions on ANY topic
✅ Perform calculations and conversions
✅ Look up definitions and explanations
✅ Remember conversations (with memory enabled)
✅ Get current weather and news (with API keys)
✅ Search the web (with API keys)
✅ Execute code safely (when enabled)

All running **locally** with Ollama! 🎉

## Cost Breakdown

| Service | Cost | Free Tier |
|---------|------|-----------|
| **Ollama LLM** | $0 | Unlimited (runs locally) |
| **Deepgram STT** | $0.0125/min | $200 credit |
| **OpenAI TTS** | $0.015/1K chars | $5 credit |
| **Weather API** | $0 | 1000 calls/day |
| **News API** | $0 | 100 calls/day |
| **Web Search** | $0 | 100 calls/month |

**Typical usage**: ~$1-2 per month for casual use with free tiers!

---

**Congratulations! 🎊** You're now ready to build amazing voice AI applications!

Next: Read [UNIVERSAL_AGENT.md](UNIVERSAL_AGENT.md) for advanced features and customization.
