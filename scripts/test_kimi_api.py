#!/usr/bin/env python3
"""Test script to verify Kimi API key functionality.

Tests both Anthropic-compatible endpoint (as used by pi-mono)
and OpenAI-compatible endpoint if available.

Usage:
    export KIMI_API_KEY="your-key-here"
    python scripts/test_kimi_api.py
"""

import json
import os
import sys
from typing import Any

import httpx

# Configuration
API_KEY = os.environ.get("KIMI_API_KEY", "")
if not API_KEY:
    print("❌ Error: KIMI_API_KEY environment variable not set")
    print("   export KIMI_API_KEY='your-key-here'")
    sys.exit(1)

# Test models
MODEL = "k2p5"  # Kimi K2.5
TEST_PROMPT = "Say 'Hello from Kimi' in exactly 3 words."

# Endpoints to test based on pi-mono and Moonshot docs
ENDPOINTS = {
    "anthropic": {
        "name": "Anthropic-Compatible (/coding/v1/messages)",
        "url": "https://api.kimi.com/coding/v1/messages",
        "headers": {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        },
        "payload": {
            "model": MODEL,
            "messages": [
                {"role": "user", "content": TEST_PROMPT}
            ],
            "max_tokens": 50,
        },
    },
    "anthropic_streaming": {
        "name": "Anthropic-Compatible (streaming)",
        "url": "https://api.kimi.com/coding/v1/messages",
        "headers": {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        },
        "payload": {
            "model": MODEL,
            "messages": [
                {"role": "user", "content": "Count from 1 to 3."}
            ],
            "max_tokens": 50,
            "stream": True,
        },
        "stream": True,
    },
    "openai": {
        "name": "OpenAI-Compatible (/coding/v1/chat/completions)",
        "url": "https://api.kimi.com/coding/v1/chat/completions",
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
        "url": "https://api.kimi.com/coding/v1/chat/completions",
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
    
    is_streaming = config.get("stream", False)
    
    try:
        with httpx.Client(timeout=30.0) as client:
            import time
            start = time.time()
            
            if is_streaming:
                # For streaming, we just check if the connection works
                with client.stream(
                    "POST",
                    config["url"],
                    headers=config["headers"],
                    json=config["payload"],
                ) as response:
                    result["latency_ms"] = round((time.time() - start) * 1000, 2)
                    
                    if response.status_code == 200:
                        # Read first chunk to verify streaming works
                        first_chunk = None
                        for chunk in response.iter_text():
                            if chunk.strip():
                                first_chunk = chunk[:200]
                                break
                        
                        result["success"] = True
                        print(f"✅ SUCCESS ({result['latency_ms']}ms) - Streaming active")
                        print(f"   First chunk: {first_chunk}...")
                    else:
                        result["error"] = f"HTTP {response.status_code}: {response.text[:200]}"
                        print(f"❌ FAILED: {result['error']}")
            else:
                # Regular non-streaming request
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
                    
                    # Anthropic-style response
                    if "content" in data and isinstance(data["content"], list):
                        for block in data["content"]:
                            if block.get("type") == "text":
                                text = block.get("text", "")
                                print(f"   Content: {text[:100]}..." if len(text) > 100 else f"   Content: {text}")
                                break
                    # OpenAI-style response
                    elif "choices" in data:
                        choice = data["choices"][0]
                        message = choice.get("message", {})
                        content = message.get("content", "")
                        print(f"   Content: {content[:100]}..." if len(content) > 100 else f"   Content: {content}")
                        
                        # Check for tool_calls
                        if "tool_calls" in message:
                            print(f"   Tool calls: {len(message['tool_calls'])}")
                    
                    # Usage info
                    if "usage" in data:
                        usage = data["usage"]
                        if "input_tokens" in usage:
                            print(f"   Tokens: {usage.get('input_tokens', 'N/A')} in / {usage.get('output_tokens', 'N/A')} out")
                        else:
                            print(f"   Tokens: {usage.get('prompt_tokens', 'N/A')} in / {usage.get('completion_tokens', 'N/A')} out")
                        
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
    print("Kimi API Key Test")
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
    
    # Determine working APIs
    anthropic_works = any(r["success"] for r in results if "anthropic" in r["name"].lower())
    openai_works = any(r["success"] for r in results if "openai" in r["name"].lower())
    
    if passed == 0:
        print("\n⚠️  WARNING: No endpoints working!")
        print("   - Verify your API key is correct")
        print("   - Check if your coding plan has API access")
        print("   - Try accessing https://www.kimi.com/code to verify key")
    elif passed == total:
        print("\n✅ All endpoints working! Your key supports full API access.")
    else:
        print("\n⚠️  Partial access - some endpoints may be limited")
    
    # Recommendation
    print("\n" + "=" * 60)
    print("RECOMMENDATION")
    print("=" * 60)
    
    if anthropic_works and openai_works:
        print("✅ Both Anthropic and OpenAI endpoints work!")
        print("   Recommendation: Use Anthropic-style for richer features")
        print("   Base URL: https://api.kimi.com/coding")
        print("   Auth: Bearer token")
    elif anthropic_works:
        print("✅ Anthropic-compatible endpoint works")
        print("   Base URL: https://api.kimi.com/coding/v1/messages")
        print("   Auth: Bearer token + anthropic-version header")
    elif openai_works:
        print("✅ OpenAI-compatible endpoint works")
        print("   Base URL: https://api.kimi.com/coding/v1/chat/completions")
        print("   Auth: Bearer token")
    else:
        print("❌ No working endpoints found")

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
