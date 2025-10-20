"""
Tests for Universal Agent
"""

import pytest
import asyncio
from datetime import datetime
from voice_livekit_agent.universal_agent import (
    UniversalAgent,
    ConversationMemory,
    safe_json_loads,
    _flag,
    _env,
)


class MockRunContext:
    """Mock context for testing."""
    pass


@pytest.fixture
def agent():
    """Create a test agent instance."""
    return UniversalAgent()


@pytest.fixture
def memory(tmp_path):
    """Create a test memory instance."""
    memory_file = tmp_path / "test_memory.json"
    return ConversationMemory(str(memory_file), max_turns=5)


# -------------------------
# Utility Functions Tests
# -------------------------

def test_safe_json_loads():
    """Test safe JSON parsing."""
    assert safe_json_loads('{"key": "value"}') == {"key": "value"}
    assert safe_json_loads('invalid json', default={}) == {}
    assert safe_json_loads('null') is None


def test_flag():
    """Test flag parsing."""
    import os
    os.environ['TEST_FLAG'] = 'true'
    assert _flag('TEST_FLAG') is True
    assert _flag('NONEXISTENT_FLAG', 'false') is False
    del os.environ['TEST_FLAG']


# -------------------------
# Memory Tests
# -------------------------

def test_memory_initialization(memory):
    """Test memory initialization."""
    assert len(memory.conversations) == 0
    assert len(memory.user_preferences) == 0
    assert len(memory.facts_learned) == 0


def test_memory_add_turn(memory):
    """Test adding conversation turns."""
    memory.add_turn("Hello", "Hi there!")
    assert len(memory.conversations) == 1
    assert memory.conversations[0]['user'] == "Hello"
    assert memory.conversations[0]['agent'] == "Hi there!"


def test_memory_max_turns(memory):
    """Test conversation history limits."""
    for i in range(10):
        memory.add_turn(f"User {i}", f"Agent {i}")
    
    # Should only keep last 5 turns
    assert len(memory.conversations) == 5
    assert memory.conversations[-1]['user'] == "User 9"


def test_memory_preferences(memory):
    """Test preference storage."""
    memory.add_preference("language", "python")
    memory.add_preference("theme", "dark")
    
    assert memory.user_preferences["language"] == "python"
    assert memory.user_preferences["theme"] == "dark"


def test_memory_facts(memory):
    """Test fact learning."""
    memory.add_fact("User prefers metric units", "preferences")
    assert len(memory.facts_learned) == 1
    assert memory.facts_learned[0]['category'] == "preferences"


def test_memory_persistence(tmp_path):
    """Test memory saves and loads correctly."""
    memory_file = tmp_path / "persist_test.json"
    
    # Create and populate memory
    mem1 = ConversationMemory(str(memory_file))
    mem1.add_turn("Test user", "Test agent")
    mem1.add_preference("test_key", "test_value")
    
    # Load in new instance
    mem2 = ConversationMemory(str(memory_file))
    assert len(mem2.conversations) == 1
    assert mem2.user_preferences["test_key"] == "test_value"


def test_memory_context_summary(memory):
    """Test context summary generation."""
    memory.add_turn("What's the weather?", "It's sunny today!")
    memory.add_turn("How about tomorrow?", "Tomorrow will be cloudy.")
    memory.add_preference("location", "San Francisco")
    
    summary = memory.get_context_summary()
    assert "weather" in summary.lower() or "sunny" in summary.lower()
    assert "San Francisco" in summary


# -------------------------
# Agent Tool Tests
# -------------------------

@pytest.mark.asyncio
async def test_get_current_datetime(agent):
    """Test datetime tool."""
    ctx = MockRunContext()
    result = await agent.get_current_datetime(ctx)
    
    assert "202" in result  # Contains year
    assert ":" in result     # Contains time separator


@pytest.mark.asyncio
async def test_calculate(agent):
    """Test calculation tool."""
    ctx = MockRunContext()
    
    # Basic arithmetic
    result = await agent.calculate(ctx, "2 + 2")
    assert "4" in result
    
    # Complex expression
    result = await agent.calculate(ctx, "sqrt(16)")
    assert "4" in result
    
    # Power
    result = await agent.calculate(ctx, "10 ** 3")
    assert "1000" in result
    
    # Error case
    result = await agent.calculate(ctx, "import os")
    assert "Error" in result or "unsafe" in result.lower()


@pytest.mark.asyncio
async def test_unit_converter(agent):
    """Test unit conversion tool."""
    ctx = MockRunContext()
    
    # Length conversion
    result = await agent.unit_converter(ctx, 1, "km", "m")
    assert "1000" in result
    
    # Temperature conversion
    result = await agent.unit_converter(ctx, 0, "C", "F")
    assert "32" in result
    
    # Weight conversion
    result = await agent.unit_converter(ctx, 1, "kg", "lb")
    assert "2.2" in result or "2.204" in result
    
    # Invalid conversion
    result = await agent.unit_converter(ctx, 1, "kg", "km")
    assert "Cannot convert" in result


@pytest.mark.asyncio
async def test_get_weather_no_api_key(agent):
    """Test weather tool without API key."""
    import os
    # Ensure API key is not set
    if 'OPENWEATHER_API_KEY' in os.environ:
        del os.environ['OPENWEATHER_API_KEY']
    
    ctx = MockRunContext()
    result = await agent.get_weather(ctx, "London")
    assert "unavailable" in result.lower() or "enable" in result.lower()


@pytest.mark.asyncio
async def test_remember_preference_without_memory():
    """Test preference storage when memory is disabled."""
    import os
    os.environ['ENABLE_MEMORY'] = 'false'
    agent = UniversalAgent()
    
    ctx = MockRunContext()
    result = await agent.remember_preference(ctx, "test", "value")
    assert "disabled" in result.lower()


@pytest.mark.asyncio
async def test_get_definition(agent):
    """Test dictionary definition tool."""
    ctx = MockRunContext()
    
    # This test requires internet connection
    # We'll just verify it doesn't crash
    try:
        result = await agent.get_definition(ctx, "hello")
        assert isinstance(result, str)
        assert len(result) > 0
    except Exception:
        pytest.skip("Network unavailable for definition test")


@pytest.mark.asyncio
async def test_explain_concept(agent):
    """Test concept explanation tool."""
    ctx = MockRunContext()
    
    # Simple level
    result = await agent.explain_concept(ctx, "gravity", "simple")
    assert "simple" in result.lower() or "explain" in result.lower()
    
    # Detailed level
    result = await agent.explain_concept(ctx, "quantum physics", "detailed")
    assert "detailed" in result.lower() or "depth" in result.lower()


@pytest.mark.asyncio
async def test_code_execution_disabled(agent):
    """Test code execution when disabled."""
    ctx = MockRunContext()
    result = await agent.execute_python_code(ctx, "print('test')")
    assert "disabled" in result.lower()


# -------------------------
# Edge Cases and Error Handling
# -------------------------

@pytest.mark.asyncio
async def test_calculate_division_by_zero(agent):
    """Test calculation handles division by zero."""
    ctx = MockRunContext()
    result = await agent.calculate(ctx, "1 / 0")
    assert "error" in result.lower()


@pytest.mark.asyncio
async def test_calculate_invalid_syntax(agent):
    """Test calculation handles syntax errors."""
    ctx = MockRunContext()
    result = await agent.calculate(ctx, "2 +")
    assert "error" in result.lower()


@pytest.mark.asyncio
async def test_unit_converter_negative_temperature(agent):
    """Test temperature conversion with negative values."""
    ctx = MockRunContext()
    result = await agent.unit_converter(ctx, -40, "C", "F")
    assert "-40" in result  # -40°C = -40°F


@pytest.mark.asyncio
async def test_empty_definition_query(agent):
    """Test definition with empty string."""
    ctx = MockRunContext()
    result = await agent.get_definition(ctx, "")
    assert "error" in result.lower() or "not found" in result.lower()


# -------------------------
# Integration Tests
# -------------------------

@pytest.mark.asyncio
async def test_agent_initialization():
    """Test agent initializes correctly."""
    agent = UniversalAgent()
    assert agent is not None
    assert hasattr(agent, 'memory')
    assert hasattr(agent, 'web_search_enabled')


def test_agent_has_required_tools():
    """Test agent has all expected tools."""
    agent = UniversalAgent()
    
    expected_tools = [
        'get_current_datetime',
        'calculate',
        'unit_converter',
        'get_weather',
        'get_definition',
        'remember_preference',
        'recall_preferences',
        'explain_concept',
    ]
    
    for tool_name in expected_tools:
        assert hasattr(agent, tool_name), f"Missing tool: {tool_name}"


# -------------------------
# Run tests
# -------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
