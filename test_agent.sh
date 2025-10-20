#!/bin/bash

# Quick Test Script for Voice Agent
# Run this to test your agent quickly

set -e  # Exit on error

echo "======================================"
echo "Voice Agent Quick Test"
echo "======================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Ollama
echo "1. Checking Ollama..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Ollama is running"
else
    echo -e "${RED}✗${NC} Ollama is NOT running"
    echo "   Start it with: ollama serve"
    exit 1
fi

# Check model
echo ""
echo "2. Checking model..."
if ollama list | grep -q "llama3.2:3b"; then
    echo -e "${GREEN}✓${NC} Model llama3.2:3b found"
else
    echo -e "${YELLOW}⚠${NC} Model not found. Pulling now..."
    ollama pull llama3.2:3b
fi

# Check .env
echo ""
echo "3. Checking configuration..."
if [ -f .env ]; then
    echo -e "${GREEN}✓${NC} .env file exists"
    
    # Check key settings
    if grep -q "USE_TOOLS=true" .env; then
        echo -e "${GREEN}✓${NC} Tools enabled"
    else
        echo -e "${YELLOW}⚠${NC} Tools not enabled (USE_TOOLS=true)"
    fi
    
    if grep -q "TTS_PROVIDER=deepgram" .env; then
        echo -e "${GREEN}✓${NC} Using Deepgram TTS"
    else
        echo -e "${YELLOW}⚠${NC} TTS provider not set to deepgram"
    fi
else
    echo -e "${RED}✗${NC} .env file not found"
    echo "   Copy .env.example to .env"
    exit 1
fi

# Check Python package
echo ""
echo "4. Checking Python package..."
if python3 -c "import voice_livekit_agent" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Package imported successfully"
else
    echo -e "${YELLOW}⚠${NC} Package import failed (may still work with uv)"
fi

# Test LLM
echo ""
echo "5. Testing LLM connection..."
BASIC_TEST=true uv run python -m voice_livekit_agent.simple_universal_agent console 2>&1 | grep -q "LLM OK" && \
    echo -e "${GREEN}✓${NC} LLM connection OK" || \
    echo -e "${RED}✗${NC} LLM test failed"

echo ""
echo "======================================"
echo "Ready to test!"
echo "======================================"
echo ""
echo "Run one of these commands:"
echo ""
echo -e "${GREEN}Recommended (Simple Agent):${NC}"
echo "  uv run python -m voice_livekit_agent.simple_universal_agent console"
echo ""
echo -e "${YELLOW}Advanced (Full Agent):${NC}"
echo "  uv run python -m voice_livekit_agent.universal_agent console"
echo ""
echo "Then try saying:"
echo "  - Hey"
echo "  - What time is it?"
echo "  - What's 2 + 2?"
echo "  - Convert 10 km to miles"
echo ""
