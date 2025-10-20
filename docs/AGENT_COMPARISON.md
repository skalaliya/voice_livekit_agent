# Agent Comparison Chart

Quick reference to help you choose the right agent for your needs.

## Feature Comparison Matrix

| Feature | Universal Agent | MCP Agent | Basic Agent | French Tutor | French Tutor+ |
|---------|----------------|-----------|-------------|--------------|---------------|
| **General Knowledge** | ✅ ALL | ✅ Good | ✅ Basic | ❌ | ❌ |
| **Error Handling** | ✅ Comprehensive | ✅ Enhanced | ⚠️ Basic | ⚠️ Basic | ⚠️ Basic |
| **Conversation Memory** | ✅ Yes | ❌ | ❌ | ✅ File-based | ✅ File-based |
| **Dynamic Tools** | ✅ API-based | ❌ | ❌ | ❌ | ❌ |
| **Calculator** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Unit Converter** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Dictionary** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Weather API** | ✅ Optional | ❌ | ❌ | ❌ | ❌ |
| **News API** | ✅ Optional | ❌ | ❌ | ❌ | ❌ |
| **Web Search** | ✅ Optional | ❌ | ❌ | ❌ | ❌ |
| **Code Execution** | ✅ Optional | ❌ | ❌ | ❌ | ❌ |
| **MCP Integration** | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Airbnb Booking** | ❌* | ✅ | ✅ | ❌ | ❌ |
| **French Learning** | ❌* | ❌ | ❌ | ✅ | ✅ |
| **Spaced Repetition** | ❌* | ❌ | ❌ | ❌ | ✅ |
| **Pronunciation** | ❌* | ❌ | ❌ | ❌ | ✅ |
| **Production Ready** | ✅ | ✅ | ⚠️ Demo | ⚠️ Demo | ⚠️ Demo |
| **Test Coverage** | ✅ High | ⚠️ Basic | ⚠️ Basic | ⚠️ Basic | ⚠️ Basic |
| **Documentation** | ✅ Complete | ⚠️ Basic | ⚠️ Basic | ⚠️ Basic | ⚠️ Basic |

*Can be added as custom tool

## Question Type Coverage

### Universal Agent ⭐
- ✅ Science & Technology
- ✅ Mathematics & Calculations  
- ✅ History & Geography
- ✅ Arts & Culture
- ✅ Health & Wellness
- ✅ Finance & Business
- ✅ Current Events
- ✅ Language & Definitions
- ✅ How-to Questions
- ✅ Explanations (ELI5 to detailed)
- ✅ Comparisons
- ✅ Trivia & Facts

### MCP Agent
- ✅ General conversation
- ✅ Airbnb bookings
- ✅ Current date/time
- ✅ Basic calculations
- ✅ Word definitions
- ⚠️ Limited domain knowledge

### Basic Agent
- ✅ General conversation
- ✅ Airbnb bookings
- ✅ Current date/time
- ⚠️ Very limited knowledge

### French Tutors
- ✅ French language learning
- ✅ Vocabulary practice
- ✅ Grammar explanations
- ✅ Roleplay scenarios
- ❌ Other topics

## Use Case Recommendations

### 🎯 Production Applications
**Recommended: Universal Agent**
- Comprehensive error handling
- Graceful degradation
- Professional quality
- Full test coverage
- Complete documentation

```bash
uv run python -m voice_livekit_agent.universal_agent console
```

### 🎓 Learning & Education
**Recommended: Universal Agent + French Tutor**
- Universal Agent for general knowledge
- French Tutor for language learning
- Both can run simultaneously

```bash
# Terminal 1: General knowledge
uv run python -m voice_livekit_agent.universal_agent console

# Terminal 2: French practice
uv run python -m voice_livekit_agent.french_voice_tutor console
```

### 🧪 Prototyping & Demos
**Recommended: Basic Agent or MCP Agent**
- Quick setup
- Simple examples
- Easy to understand

```bash
uv run python -m voice_livekit_agent.livekit_basic_agent console
```

### 🗣️ Language Learning
**Recommended: French Tutor Plus**
- Spaced repetition
- Pronunciation practice
- Progress tracking
- Daily reminders

```bash
uv run python -m voice_livekit_agent.french_voice_tutor_plus console
```

### 🏢 Enterprise Applications
**Recommended: Universal Agent (customized)**
- Add your domain-specific tools
- Integrate with your APIs
- Full error handling built-in
- Scalable architecture

```python
# Extend universal_agent.py with your tools
@function_tool
async def your_enterprise_tool(...):
    ...
```

## Performance Comparison

| Agent | Startup | Response | Memory | Quality |
|-------|---------|----------|--------|---------|
| Universal | ~3s | 1-3s | ~600MB | ⭐⭐⭐⭐⭐ |
| MCP | ~2s | 1-2s | ~500MB | ⭐⭐⭐⭐ |
| Basic | ~2s | 1-2s | ~450MB | ⭐⭐⭐ |
| French | ~2s | 1-2s | ~500MB | ⭐⭐⭐⭐ |
| French+ | ~2s | 1-2s | ~550MB | ⭐⭐⭐⭐ |

## Setup Complexity

| Agent | Setup Time | Required Keys | Difficulty |
|-------|-----------|---------------|------------|
| Universal | 5 min | None (basic) / 2-3 (full) | ⭐ Easy |
| MCP | 5 min | None (basic) / 2 (voice) | ⭐ Easy |
| Basic | 5 min | None (basic) / 2 (voice) | ⭐ Easy |
| French | 5 min | None (basic) / 2 (voice) | ⭐ Easy |
| French+ | 5 min | None (basic) / 2 (voice) | ⭐ Easy |

**Required Keys:**
- Basic: Just Ollama (free, local)
- Voice: + Deepgram + OpenAI TTS
- Full: + Weather + News + Search (all optional)

## Cost Comparison (Monthly)

| Agent | LLM | STT | TTS | APIs | Total |
|-------|-----|-----|-----|------|-------|
| Universal (basic) | $0 | - | - | - | **$0** |
| Universal (voice) | $0 | ~$1 | ~$0.50 | - | **~$1.50** |
| Universal (full) | $0 | ~$1 | ~$0.50 | $0 | **~$1.50** |
| Others (voice) | $0 | ~$1 | ~$0.50 | - | **~$1.50** |

*Assumes free API tiers, casual use (~30 min/month voice, 100 API calls)*

## Migration Difficulty

| From → To | Difficulty | Time | Breaking Changes |
|-----------|-----------|------|------------------|
| Basic → Universal | ⭐ Easy | 5 min | None (tools differ) |
| MCP → Universal | ⭐ Easy | 5 min | None (tools differ) |
| French → Universal | ⭐⭐ Medium | 10 min | Need custom tools |
| Any → Any | ⭐ Easy | 5 min | .env changes only |

See [Migration Guide](MIGRATION_GUIDE.md) for details.

## Decision Flowchart

```
Start
│
├─ Need language learning?
│  └─ YES → French Tutor (Basic) or French Tutor+ (Advanced)
│
├─ Need MCP integration?
│  └─ YES → MCP Agent
│
├─ Production application?
│  └─ YES → Universal Agent ⭐
│
├─ Learning/Demo?
│  └─ YES → Basic Agent
│
└─ Handle any question?
   └─ YES → Universal Agent ⭐
```

## Quick Selection Guide

Choose **Universal Agent** if you want:
- ✅ Production-ready quality
- ✅ Handle diverse questions
- ✅ Built-in error handling
- ✅ Conversation memory
- ✅ Extensible tools
- ✅ Full documentation

Choose **MCP Agent** if you want:
- ✅ Model Context Protocol features
- ✅ Enhanced basic capabilities
- ⚠️ Limited to specific domains

Choose **Basic Agent** if you want:
- ✅ Simple demo
- ✅ Learning example
- ⚠️ Minimal features

Choose **French Tutors** if you want:
- ✅ Language learning
- ✅ Pronunciation practice
- ⚠️ French only

## Summary Recommendation

**For 90% of use cases: Start with Universal Agent** ⭐

It's the most capable, reliable, and well-documented option. You can always add specialized features from other agents as custom tools.

---

**Still unsure?** Check our [Quick Start Guide](QUICKSTART.md) or open a discussion on GitHub!
