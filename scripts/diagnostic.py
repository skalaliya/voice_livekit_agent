#!/usr/bin/env python3
"""
System Diagnostic Tool
Run this to check your setup and identify issues.
"""

import os
import sys
import subprocess
import requests
from pathlib import Path

def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print('='*60)

def check_mark(success):
    return "✓" if success else "✗"

def test_ollama():
    print_header("Testing Ollama")
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=3)
        if response.status_code == 200:
            models = response.json().get('models', [])
            print(f"{check_mark(True)} Ollama is running")
            print(f"   Found {len(models)} model(s):")
            for model in models:
                print(f"   - {model['name']}")
            return True
        else:
            print(f"{check_mark(False)} Ollama returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"{check_mark(False)} Cannot connect to Ollama on port 11434")
        print("   Fix: Run 'ollama serve' in another terminal")
        return False
    except Exception as e:
        print(f"{check_mark(False)} Error: {e}")
        return False

def test_llm():
    print_header("Testing LLM Communication")
    try:
        response = requests.post(
            "http://127.0.0.1:11434/v1/chat/completions",
            headers={"Authorization": "Bearer ollama"},
            json={
                "model": "llama3.2:3b",
                "messages": [{"role": "user", "content": "Say OK"}],
                "max_tokens": 10
            },
            timeout=30
        )
        if response.status_code == 200:
            result = response.json()
            message = result['choices'][0]['message']['content']
            print(f"{check_mark(True)} LLM responding correctly")
            print(f"   Response: {message}")
            return True
        else:
            print(f"{check_mark(False)} LLM returned status {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"{check_mark(False)} Error: {e}")
        return False

def check_env_file():
    print_header("Checking .env Configuration")
    env_path = Path(".env")
    
    if not env_path.exists():
        print(f"{check_mark(False)} .env file not found")
        print("   Fix: Copy .env.example to .env")
        return False
    
    print(f"{check_mark(True)} .env file exists")
    
    required = {
        "OPENAI_BASE_URL": "http://127.0.0.1:11434/v1",
        "OPENAI_API_KEY": "ollama",
        "LLM_MODEL": "llama3.2:3b"
    }
    
    with open(env_path) as f:
        content = f.read()
    
    all_good = True
    for key, expected in required.items():
        if key in content:
            # Extract value
            for line in content.split('\n'):
                if line.startswith(f"{key}="):
                    value = line.split('=', 1)[1].strip()
                    match = value == expected
                    print(f"   {check_mark(match)} {key}={'✓' if match else f'(got: {value})'}")
                    if not match:
                        all_good = False
                    break
        else:
            print(f"   {check_mark(False)} {key} missing")
            all_good = False
    
    # Check optional settings
    optional_checks = {
        "USE_TOOLS": "true",
        "TTS_PROVIDER": "deepgram",
        "BASIC_TEST": "false"
    }
    
    print("\n   Optional settings:")
    for key, recommended in optional_checks.items():
        if key in content:
            for line in content.split('\n'):
                if line.startswith(f"{key}="):
                    value = line.split('=', 1)[1].strip()
                    print(f"   • {key}={value}")
                    break
        else:
            print(f"   • {key} not set (recommended: {recommended})")
    
    return all_good

def check_api_keys():
    print_header("Checking API Keys")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    deepgram_key = os.getenv("DEEPGRAM_API_KEY")
    openai_tts_key = os.getenv("OPENAI_TTS_API_KEY")
    tts_provider = os.getenv("TTS_PROVIDER", "openai")
    
    if deepgram_key:
        masked = deepgram_key[:10] + "..." if len(deepgram_key) > 10 else "***"
        print(f"{check_mark(True)} DEEPGRAM_API_KEY set ({masked})")
    else:
        print(f"{check_mark(False)} DEEPGRAM_API_KEY not set")
        print("   Voice STT will not work")
    
    if tts_provider.lower() == "deepgram":
        print(f"{check_mark(True)} TTS Provider: Deepgram (uses same key as STT)")
    elif openai_tts_key:
        masked = openai_tts_key[:10] + "..." if len(openai_tts_key) > 10 else "***"
        print(f"{check_mark(True)} OPENAI_TTS_API_KEY set ({masked})")
    else:
        print(f"{check_mark(False)} OPENAI_TTS_API_KEY not set")
        print("   Voice TTS will not work")

def test_imports():
    print_header("Testing Python Imports")
    
    modules = [
        "livekit.agents",
        "livekit.plugins.openai",
        "livekit.plugins.deepgram",
        "livekit.plugins.silero",
        "voice_livekit_agent.simple_universal_agent",
        "voice_livekit_agent.universal_agent"
    ]
    
    all_good = True
    for module in modules:
        try:
            __import__(module)
            print(f"{check_mark(True)} {module}")
        except ImportError as e:
            print(f"{check_mark(False)} {module} - {e}")
            all_good = False
    
    return all_good

def run_quick_test():
    print_header("Running Quick Agent Test")
    
    try:
        from voice_livekit_agent.simple_universal_agent import _basic_test
        _basic_test()
        return True
    except Exception as e:
        print(f"{check_mark(False)} Test failed: {e}")
        return False

def main():
    print("\n🔍 Voice Agent System Diagnostic")
    print("=" * 60)
    
    results = {
        "Ollama": test_ollama(),
        "LLM": test_llm(),
        "Environment": check_env_file(),
        "Imports": test_imports(),
        "Quick Test": run_quick_test()
    }
    
    check_api_keys()
    
    print_header("Summary")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, success in results.items():
        print(f"{check_mark(success)} {name}")
    
    print(f"\n{passed}/{total} checks passed")
    
    if passed == total:
        print("\n✓ All systems operational!")
        print("\nYou can now run:")
        print("  uv run python -m voice_livekit_agent.simple_universal_agent console")
    else:
        print("\n✗ Some issues detected. See above for fixes.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
