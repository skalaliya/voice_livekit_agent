#!/bin/bash
# Quick test script for the simple universal agent

cd "$(dirname "$0")/.."

echo "🚀 Starting Simple Universal Agent Test..."
echo ""

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✓ Virtual environment activated"
else
    echo "✗ No .venv found. Run 'uv sync' first"
    exit 1
fi

# Test basic mode first
echo ""
echo "Testing LLM connection..."
BASIC_TEST=true python -m voice_livekit_agent.simple_universal_agent console 2>&1 | head -20

echo ""
echo "If you saw '✓ LLM OK', you're ready!"
echo ""
echo "To run with voice:"
echo "  source .venv/bin/activate"
echo "  python -m voice_livekit_agent.simple_universal_agent console"
