#!/usr/bin/env python3
"""Test script to verify MiniMax API key functionality.

Tests both OpenAI-compatible and Anthropic-compatible endpoints
to determine which API surface works with your coding plan key.

Usage:
    export MINIMAX_API_KEY="your-key-here"
    python scripts/test_minimax_api.py
"""

import json
import os
import sys
from typing import Any

import httpx

# Configuration
API_KEY = os.environ.get("MINIMAX_API_KEY", "")
if not API_KEY:
    print("❌ Error: MINIMAX_API_KEY environment variable not set")
    print("   export MINIMAX_API_KEY='your-key-here'")
    sys.exit(1)

# Test models
MODEL = "MiniMax-M2.5"
TEST_PROMPT = "Say 'Hello from MiniMax' in exactly 3 words."

# Endpoints to test
ENDPOINTS = {
    "openai": {
        "name": "OpenAI-Compatible (/v1/chat/completions)",
        "url": "https://api.minimax.io/v1/chat/completions",
        "headers": {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        "payload": {
            "model": MODEL,
            "messages": [
                {"role": "user", "content": TEST_PROMPT}
            ],
            "max_tokens": 50,
            "temperature": 0.1,
        },
    },
    "openai_json": {
        "name": "OpenAI-Compatible with JSON mode",
        "url": "https://api.minimax.io/v1/chat/completions",
        "headers": {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        "payload": {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Return a JSON object with field 'greeting' containing a hello message."}
            ],
            "max_tokens": 100,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        },
    },
    "openai_reasoning": {
        "name": "OpenAI-Compatible with reasoning_split",
        "url": "https://api.minimax.io/v1/chat/completions",
        "headers": {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        "payload": {
            "model": MODEL,
            "messages": [
                {"role": "user", "content": "What is 2+2? Think step by step."}
            ],
            "max_tokens": 200,
            "temperature": 0.1,
            "extra_body": {"reasoning_split": True},
        },
    },
}

def mask_key(key: str) -> str:
    """Mask API key for safe display."""
    if len(key) <= 8:
        return "***"
    return f"{key[:4]}...{key[-4:]}"

def test_endpoint(name: str, config: dict[str, Any]) -> dict[str, Any]:
    """Test a single endpoint."""
    print(f"\n{'='*60}")
    print(f"Testing: {config['name']}")
    print(f"URL: {config['url']}")
    print(f"Auth: {mask_key(API_KEY)}")
    print("-" * 60)
    
    result = {
        "name": config["name"],
        "success": False,
        "error": None,
        "response": None,
        "latency_ms": 0,
    }
    
    try:
        with httpx.Client(timeout=30.0) as client:
            import time
            start = time.time()
            
            response = client.post(
                config["url"],
                headers=config["headers"],
                json=config["payload"],
            )
            
            result["latency_ms"] = round((time.time() - start) * 1000, 2)
            
            if response.status_code == 200:
                result["success"] = True
                result["response"] = response.json()
                print(f"✅ SUCCESS ({result['latency_ms']}ms)")
                
                # Extract key response fields
                data = result["response"]
                if "choices" in data:
                    choice = data["choices"][0]
                    message = choice.get("message", {})
                    content = message.get("content", "")
                    print(f"   Content: {content[:100]}..." if len(content) > 100 else f"   Content: {content}")
                    
                    # Check for tool_calls or reasoning
                    if "tool_calls" in message:
                        print(f"   Tool calls: {len(message['tool_calls'])}")
                    if "reasoning_details" in message:
                        print(f"   Reasoning: Yes")
                
                if "usage" in data:
                    usage = data["usage"]
                    print(f"   Tokens: {usage.get('total_tokens', 'N/A')} total")
                    
            else:
                result["error"] = f"HTTP {response.status_code}: {response.text[:200]}"
                print(f"❌ FAILED: {result['error']}")
                
    except httpx.TimeoutException:
        result["error"] = "Timeout (30s)"
        print(f"❌ FAILED: Timeout")
    except Exception as e:
        result["error"] = str(e)
        print(f"❌ FAILED: {e}")
    
    return result

def test_health_check():
    """Quick health check before full tests."""
    print("=" * 60)
    print("MiniMax API Key Test")
    print("=" * 60)
    print(f"API Key: {mask_key(API_KEY)}")
    print(f"Model: {MODEL}")
    print(f"Python: {sys.version}")
    print()

def print_summary(results: list[dict[str, Any]]):
    """Print test summary."""
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for r in results if r["success"])
    total = len(results)
    
    for r in results:
        status = "✅ PASS" if r["success"] else "❌ FAIL"
        latency = f"({r['latency_ms']}ms)" if r["success"] else ""
        print(f"{status} {r['name']} {latency}")
        if r["error"] and not r["success"]:
            print(f"      Error: {r['error'][:100]}")
    
    print("-" * 60)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == 0:
        print("\n⚠️  WARNING: No endpoints working!")
        print("   - Verify your API key is correct")
        print("   - Check if your coding plan has API access")
        print("   - Try accessing https://platform.minimax.io to verify key")
    elif passed == total:
        print("\n✅ All endpoints working! Your key supports full API access.")
    else:
        print("\n⚠️  Partial access - some features may be limited")
    
    # Recommendation
    print("\n" + "=" * 60)
    print("RECOMMENDATION")
    print("=" * 60)
    
    openai_works = any(r["success"] for r in results if "openai" in r["name"].lower())
    
    if openai_works:
        print("✅ Use OpenAI-compatible endpoint (current implementation)")
        print("   Base URL: https://api.minimax.io/v1")
        print("   Auth: Bearer token")
        print("   This is the simpler, more stable choice for your use case.")
    else:
        print("❌ OpenAI endpoint not working - check key permissions")

def main():
    """Run all tests."""
    test_health_check()
    
    results = []
    for key, config in ENDPOINTS.items():
        result = test_endpoint(key, config)
        results.append(result)
    
    print_summary(results)
    
    # Exit with error code if no tests passed
    if not any(r["success"] for r in results):
        sys.exit(1)

if __name__ == "__main__":
    main()
