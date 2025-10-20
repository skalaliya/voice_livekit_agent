# Universal Voice Agent - Complete Guide

## 🚀 Overview

The Universal Voice Agent is a **robust, production-ready AI assistant** that can handle **ANY type of question** across all domains. Unlike specialized agents, this universal agent combines:

- **Comprehensive Error Handling**: Graceful degradation when services are unavailable
- **Dynamic Tool Registration**: Automatically enables features based on available API keys
- **Conversation Memory**: Persistent context tracking across sessions
- **Multi-Domain Knowledge**: Science, tech, history, math, travel, health, finance, and more
- **Extensible Architecture**: Easy to add new capabilities

## 🎯 Quick Start

### 1. Install Dependencies

```bash
# Install using uv (recommended)
uv sync

# Or using pip
pip install -r requirements.txt
```

### 2. Setup Ollama (Local LLM)

```bash
# Install Ollama from https://ollama.ai
# Pull a model
ollama pull llama3.2:3b

# Start the server (keep running)
ollama serve
```

### 3. Configure Environment

```bash
# Copy example config
cp .env.example .env

# Edit .env with your settings
# Minimum for testing:
OPENAI_BASE_URL=http://127.0.0.1:11434/v1
OPENAI_API_KEY=ollama
LLM_MODEL=llama3.2:3b
BASIC_TEST=true
```

### 4. Run Your First Test

```bash
# Test LLM connectivity (no audio needed)
uv run python -m voice_livekit_agent.universal_agent console
```

### 5. Enable Voice Mode

```bash
# Get API keys (free tiers available):
# - Deepgram STT: https://deepgram.com/
# - OpenAI TTS: https://platform.openai.com/

# Add to .env:
BASIC_TEST=false
DEEPGRAM_API_KEY=your_key_here
OPENAI_TTS_API_KEY=your_key_here
USE_TOOLS=true

# Run with voice
uv run python -m voice_livekit_agent.universal_agent console
```

## 🛠️ Features & Capabilities

### Core Tools (Always Available)

| Tool | Description | Example Questions |
|------|-------------|-------------------|
| **DateTime** | Current date, time, timezone | "What time is it?", "What day is today?" |
| **Calculator** | Math operations, functions | "What's 15% of 250?", "Calculate sqrt(144)" |
| **Unit Converter** | Length, weight, temperature, volume | "Convert 5 km to miles", "32°F in Celsius?" |
| **Dictionary** | Word definitions, examples | "What does 'ephemeral' mean?" |
| **Concept Explainer** | ELI5 to detailed explanations | "Explain quantum physics simply" |

### Optional Tools (Requires API Keys)

| Tool | API Required | Description |
|------|-------------|-------------|
| **Weather** | OpenWeather | Current conditions, forecasts |
| **News Search** | NewsAPI | Latest articles by topic |
| **Web Search** | SerpAPI | General web searches |
| **Code Execution** | None (sandbox) | Run Python code safely |

### Conversation Memory

When `ENABLE_MEMORY=true`:
- Remembers previous conversations
- Stores user preferences
- Learns facts about the user
- Provides context-aware responses

```python
# Example conversation:
User: "I prefer metric units"
Agent: "I'll remember that: units = metric"

# Later...
User: "What's the temperature in Paris?"
Agent: "Currently 18°C in Paris" # Uses remembered preference
```

## 📚 Example Conversations

### General Knowledge

```
You: "Explain photosynthesis"
Agent: "Photosynthesis is how plants make food using sunlight..."

You: "Who won the World Cup in 2018?"
Agent: "France won the 2018 FIFA World Cup..."

You: "What's the capital of Peru?"
Agent: "The capital of Peru is Lima..."
```

### Mathematics & Calculations

```
You: "What's 15% of 850?"
Agent: [calls calculate tool] "Result: 127.5"

You: "Convert 100 fahrenheit to celsius"
Agent: [calls unit_converter] "100 F = 37.78 C"

You: "Calculate the area of a circle with radius 5"
Agent: [uses calculator] "Result: 78.54 square units (π × 5²)"
```

### Current Information

```
You: "What's the weather in London?"
Agent: [calls weather API] "Currently 15°C, cloudy with 70% humidity..."

You: "Latest news about AI?"
Agent: [searches news] "Here are the top 5 recent AI articles..."

You: "What time is it?"
Agent: "Monday, October 20, 2025 at 3:45 PM"
```

### Language & Definitions

```
You: "Define 'serendipity'"
Agent: [looks up definition] "'Serendipity': The occurrence of events by chance..."

You: "What's another word for happy?"
Agent: "Synonyms for happy include: joyful, content, pleased, delighted..."
```

### Complex Questions

```
You: "Why is the sky blue?"
Agent: "The sky appears blue due to Rayleigh scattering. When sunlight enters Earth's atmosphere, it collides with air molecules. Blue light has a shorter wavelength and scatters more than other colors, making the sky appear blue to our eyes."

You: "How does Bitcoin work?"
Agent: "Bitcoin is a decentralized digital currency... [detailed explanation with key concepts]"
```

## 🔧 Configuration Guide

### Environment Variables

#### Core Settings (Required)

```bash
# LLM Configuration
OPENAI_BASE_URL=http://127.0.0.1:11434/v1  # Ollama endpoint
OPENAI_API_KEY=ollama                       # Dummy key for Ollama
LLM_MODEL=llama3.2:3b                       # Model to use
LLM_TEMPERATURE=0.7                         # 0.0-1.0, higher = more creative
```

#### Testing & Startup

```bash
BASIC_TEST=true          # true = LLM test only, false = full voice mode
WARMUP_LLM=true          # Preload model to reduce first response time
WARMUP_TIMEOUT=60        # Seconds to wait for warmup
```

#### Voice Pipeline

```bash
# When BASIC_TEST=false
DEEPGRAM_API_KEY=xxx     # Speech-to-text
DEEPGRAM_MODEL=nova-2    # STT model choice

OPENAI_TTS_API_KEY=xxx   # Text-to-speech
TTS_VOICE=alloy          # Voice: alloy, echo, fable, onyx, nova, shimmer
OPENAI_TTS_BASE_URL=...  # Default: https://api.openai.com/v1
```

#### Features

```bash
USE_TOOLS=true           # Enable/disable function tools
ENABLE_MEMORY=true       # Persistent conversation tracking
MEMORY_FILE=agent_memory.json
MAX_CONTEXT_TURNS=10     # How many turns to remember

ENABLE_WEB_SEARCH=false  # Requires SERPAPI_KEY
ENABLE_CODE_EXEC=false   # Sandbox Python execution
```

#### Optional Services

```bash
OPENWEATHER_API_KEY=xxx  # Free tier: https://openweathermap.org/
NEWS_API_KEY=xxx         # Free tier: https://newsapi.org/
SERPAPI_KEY=xxx          # Free tier: https://serpapi.com/
```

### Model Selection

| Model | Size | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| llama3.2:1b | 1B params | ⚡⚡⚡ | ⭐⭐ | Quick responses, simple queries |
| llama3.2:3b | 3B params | ⚡⚡ | ⭐⭐⭐ | Balanced (recommended) |
| llama3:8b | 8B params | ⚡ | ⭐⭐⭐⭐ | Complex reasoning |
| mixtral:8x7b | 47B params | 🐌 | ⭐⭐⭐⭐⭐ | Best quality, slower |

```bash
# Change model in .env
LLM_MODEL=llama3.2:3b

# Or use environment variable
export LLM_MODEL=llama3:8b
```

## 🧪 Testing

### Run All Tests

```bash
# Using pytest
pytest tests/ -v

# With coverage
pytest tests/ --cov=voice_livekit_agent --cov-report=html

# Specific test file
pytest tests/test_universal_agent.py -v
```

### Manual Testing

```bash
# Test LLM only (no API keys needed)
BASIC_TEST=true uv run python -m voice_livekit_agent.universal_agent console

# Test with voice (requires Deepgram + OpenAI TTS keys)
BASIC_TEST=false uv run python -m voice_livekit_agent.universal_agent console

# Test specific tools
python -c "
from voice_livekit_agent.universal_agent import UniversalAgent
import asyncio

async def test():
    agent = UniversalAgent()
    class MockContext: pass
    ctx = MockContext()
    
    # Test calculator
    result = await agent.calculate(ctx, '2 + 2')
    print(f'Calculator: {result}')
    
    # Test datetime
    result = await agent.get_current_datetime(ctx)
    print(f'DateTime: {result}')

asyncio.run(test())
"
```

## 🐛 Troubleshooting

### Common Issues

#### 1. "Model not found" Error

```bash
# Solution: Pull the model
ollama pull llama3.2:3b

# Verify it's available
ollama list
```

#### 2. "Connection refused" on port 11434

```bash
# Solution: Start Ollama server
ollama serve

# Check if it's running
curl http://localhost:11434/api/tags
```

#### 3. First Response Very Slow

```bash
# Solution: Enable warmup
WARMUP_LLM=true  # in .env

# Or increase timeout
WARMUP_TIMEOUT=120
```

#### 4. "Missing environment variables" Error

```bash
# Solution: Check your .env file
cat .env

# Ensure you have at minimum:
OPENAI_BASE_URL=http://127.0.0.1:11434/v1
OPENAI_API_KEY=ollama
LLM_MODEL=llama3.2:3b
```

#### 5. Tools Not Working

```bash
# Solution: Enable tools explicitly
USE_TOOLS=true  # in .env

# Or for specific features
ENABLE_MEMORY=true
ENABLE_WEB_SEARCH=true  # Requires SERPAPI_KEY
```

#### 6. Audio Not Working

```bash
# Check API keys are set
grep -E "DEEPGRAM|TTS" .env

# Ensure BASIC_TEST is false
BASIC_TEST=false

# Verify microphone access (macOS)
# System Settings → Privacy & Security → Microphone → Terminal
```

### Debug Mode

```bash
# Enable verbose logging
export LOG_LEVEL=DEBUG

# Run with debug output
uv run python -m voice_livekit_agent.universal_agent console 2>&1 | tee debug.log
```

## 🔌 Extending the Agent

### Adding New Tools

```python
# In universal_agent.py

@function_tool
async def your_new_tool(
    self,
    context: RunContext,
    param1: str,
    param2: int = 10
) -> str:
    """
    Description of what your tool does.
    
    Args:
        param1: Description of param1
        param2: Description of param2 (default: 10)
    
    Returns:
        String result to show to user
    """
    try:
        # Your tool logic here
        result = do_something(param1, param2)
        return f"Success: {result}"
    except Exception as e:
        return f"Error: {str(e)}"
```

### Adding New API Integrations

```python
# Example: Add currency conversion

@function_tool
async def convert_currency(
    self,
    context: RunContext,
    amount: float,
    from_currency: str,
    to_currency: str
) -> str:
    """Convert between currencies using live exchange rates."""
    api_key = _env("EXCHANGE_RATE_API_KEY")
    if not api_key:
        return "Currency conversion unavailable. Set EXCHANGE_RATE_API_KEY"
    
    try:
        url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
        response = safe_request(url)
        if not response:
            return f"Could not fetch exchange rates"
        
        data = response.json()
        rate = data['rates'][to_currency.upper()]
        result = amount * rate
        
        return f"{amount} {from_currency} = {result:.2f} {to_currency}"
    except Exception as e:
        return f"Conversion error: {str(e)}"
```

## 📊 Performance Tips

### Optimize Response Time

1. **Use Smaller Models for Simple Queries**
   ```bash
   LLM_MODEL=llama3.2:1b  # Fast, good for basic questions
   ```

2. **Enable Warmup**
   ```bash
   WARMUP_LLM=true  # Preloads model
   ```

3. **Adjust Temperature**
   ```bash
   LLM_TEMPERATURE=0.3  # Lower = faster, more deterministic
   ```

4. **Limit Context**
   ```bash
   MAX_CONTEXT_TURNS=5  # Fewer turns = faster processing
   ```

### Manage Memory Usage

```bash
# Use smaller models
ollama pull llama3.2:1b  # ~1GB RAM

# vs larger models
ollama pull llama3:70b   # ~40GB RAM
```

### Cost Optimization

- **Deepgram STT**: ~$0.0125 per minute (pay-as-you-go)
- **OpenAI TTS**: ~$0.015 per 1K characters
- **Ollama LLM**: Free (runs locally)
- **Weather/News APIs**: Free tiers available

**Tip**: Use BASIC_TEST=true for development to avoid STT/TTS costs.

## 🤝 Contributing

### Adding Tests

```python
# tests/test_universal_agent.py

@pytest.mark.asyncio
async def test_your_feature(agent):
    """Test description."""
    ctx = MockRunContext()
    result = await agent.your_tool(ctx, "test_input")
    assert "expected" in result
```

### Code Style

```bash
# Format code
black voice_livekit_agent/

# Check linting
ruff check voice_livekit_agent/

# Type checking
mypy voice_livekit_agent/
```

## 📝 License

This project is licensed under the MIT License. See LICENSE file for details.

## 🙏 Credits

- **LiveKit Agents**: Core framework
- **Ollama**: Local LLM runtime
- **Deepgram**: Speech-to-text
- **OpenAI**: Text-to-speech
- **Silero VAD**: Voice activity detection

---

**Need Help?** Open an issue on GitHub or check our documentation at [link].

**Want to Contribute?** Pull requests are welcome! See CONTRIBUTING.md for guidelines.
