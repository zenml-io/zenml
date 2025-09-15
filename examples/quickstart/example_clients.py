#!/usr/bin/env python3
"""Example client usage for the English translation serving endpoint.

This script shows practical examples of how to integrate the translation
endpoint into real applications.
"""

from typing import Any, Dict, Optional

import requests

# Configuration
ENDPOINT_URL = "http://localhost:8001"  # Update with your deployment URL
AUTH_KEY = None  # Set if authentication is enabled


def translate_text(text: str) -> Dict[str, Any]:
    """Translate old English text to modern English.
    
    Args:
        text: The old English text to translate
        
    Returns:
        Translation result from the API
    """
    payload = {"input": text}
    
    return _call_api(payload, "Translation")


def _call_api(payload: Dict[str, Any], operation_name: str) -> Dict[str, Any]:
    """Make API call to the translation endpoint."""
    headers = {"Content-Type": "application/json"}
    if AUTH_KEY:
        headers["Authorization"] = f"Bearer {AUTH_KEY}"

    try:
        print(f"🔄 {operation_name}...")

        response = requests.post(
            f"{ENDPOINT_URL}/invoke", json=payload, headers=headers, timeout=60
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ {operation_name} completed successfully")
            return result
        else:
            print(f"❌ {operation_name} failed: {response.status_code}")
            print(f"Error: {response.text}")
            return {}

    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to {ENDPOINT_URL}")
        print("Make sure the serving endpoint is running!")
        return {}

    except Exception as e:
        print(f"❌ {operation_name} error: {e}")
        return {}


def extract_translation(api_response: Dict[str, Any]) -> Optional[str]:
    """Extract translation from API response."""
    if "outputs" in api_response:
        return api_response["outputs"]
    return None


def print_translation_result(original: str, translation: str) -> None:
    """Print a formatted translation result."""
    if not translation:
        print("No translation available")
        return
        
    print("\n📝 Translation Result:")
    print("=" * 50)
    print(f"Original:    {original}")
    print(f"Translation: {translation}")
    print("=" * 50)


def main():
    """Example usage scenarios for the translation API."""
    print("🧪 English Translation API - Example Usage")
    print("=" * 60)
    
    # Example translations
    test_cases = [
        {
            "text": "Ye olde knight rode through the forest",
            "context": "Medieval narrative"
        },
        {
            "text": "Thou art a brave warrior, good sir",
            "context": "Character dialogue"
        },
        {
            "text": "Methinks the weather doth appear fair this day",
            "context": "Weather observation"
        },
        {
            "text": "I pray thee, tell me the way to the nearest tavern",
            "context": "Asking for directions"
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n{i}️⃣ Example {i}: {case['context']}")
        print(f"Input: \"{case['text']}\"")
        
        result = translate_text(case["text"])
        translation = extract_translation(result)
        print_translation_result(case["text"], translation)
    
    print("\n🎉 All examples completed!")
    print("\n📋 Integration Tips:")
    print("• Use the translation API for modernizing historical texts")
    print("• Batch process multiple texts by sending separate requests")
    print("• Check the response status before processing results")
    print("• Handle network errors and timeouts appropriately")
    print("• Consider caching translations for frequently used phrases")


if __name__ == "__main__":
    main()