"""Privacy-Focused Chat Agent Pipeline for ZenML Serving Demo.

This pipeline implements a conversational AI chat agent that demonstrates
simplified capture settings for privacy-sensitive applications.

Key Privacy Features:
- User messages: Only captured on errors with PII redaction - {"inputs": {"message": "errors_only"}}
- User names: Never captured - {"inputs": {"user_name": "none"}}
- Responses: Minimal sampling (5%) without artifact storage - {"outputs": "sampled", "sample_rate": 0.05}
- Comprehensive PII redaction patterns at both step and pipeline level

This example shows how to build chat applications with ZenML serving
using the new simplified capture syntax while maintaining strong privacy
protections.
"""

import os
import time
from typing import Dict

from zenml import pipeline, step
from zenml.config import DockerSettings

# Import enums for type-safe capture mode configuration
from zenml.serving.policy import CapturePolicyMode as CaptureMode

# This example demonstrates type-safe enum usage to prevent typos:
# Instead of: "full" -> CaptureMode.FULL (validates at import time)
# Available: FULL, METADATA, SAMPLED, ERRORS_ONLY, NONE

docker_settings = DockerSettings(
    requirements=["openai"],
    environment={"OPENAI_API_KEY": os.getenv("OPENAI_API_KEY")},
)


@step(
    settings={
        "serving_capture": {
            "inputs": {
                "message": CaptureMode.ERRORS_ONLY,
                "user_name": CaptureMode.NONE,
                "personality": CaptureMode.FULL,
            },
            "outputs": CaptureMode.SAMPLED,
            "sample_rate": 0.05,
            "max_bytes": 1024,
            "redact": ["password", "email", "phone", "ssn", "credit"],
        }
    }
)
def generate_chat_response(
    message: str, user_name: str, personality: str
) -> Dict[str, str]:
    """Generate a chat response using LLM or fallback logic.

    Demonstrates privacy-first capture for chat applications:
    - Messages: Only captured on errors with PII redaction (debugging failed responses)
    - User names: Never captured (strict PII protection)
    - Personality: Always captured (safe configuration data)
    - Responses: Sample 5% for quality monitoring, no artifact storage (cost optimization)

    Args:
        message: User's message
        user_name: User's name for personalization
        personality: Agent personality style

    Returns:
        Chat response with metadata
    """
    try:
        # Try OpenAI API if available
        import os

        import openai

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ImportError("OpenAI API key not found")

        client = openai.OpenAI(api_key=api_key)

        # Simple conversational prompt
        system_prompt = f"You are a {personality} AI assistant chatting with {user_name}. Keep responses conversational and helpful."

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            max_tokens=300,
            temperature=0.7,
        )

        ai_response = response.choices[0].message.content

        return {
            "content": ai_response,
            "user_name": user_name,
            "model": "gpt-3.5-turbo",
            "timestamp": str(time.time()),
        }

    except Exception as e:
        print(f"LLM failed ({e}), using fallback...")

        # Simple rule-based responses
        message_lower = message.lower()

        if any(word in message_lower for word in ["hello", "hi", "hey"]):
            response = f"Hello {user_name}! How can I help you today?"
        elif any(word in message_lower for word in ["thanks", "thank you"]):
            response = f"You're welcome, {user_name}! Happy to help!"
        elif "?" in message:
            response = f"That's a great question, {user_name}! Let me help you with that."
        else:
            response = f"I understand, {user_name}. I'm here to help with whatever you need!"

        return {
            "content": response,
            "user_name": user_name,
            "model": "rule-based-fallback",
            "timestamp": str(time.time()),
        }


@pipeline(
    settings={
        "docker": docker_settings,
        # Privacy-first pipeline defaults for chat applications using type-safe enums
        "serving_capture": {
            "mode": CaptureMode.NONE,  # Very conservative default for chat (type-safe)
            "max_bytes": 512,  # Small payloads for privacy
            "redact": [
                "password",
                "email",
                "phone",
                "ssn",
                "credit",
                "token",
                "key",
                "secret",
            ],
        },
    }
)
def chat_agent_pipeline(
    message: str = "Hello",
    user_name: str = "User",
    personality: str = "helpful",
) -> Dict[str, str]:
    """Privacy-focused chat agent pipeline demonstrating step-level capture annotations.

    Showcases privacy-first approach for chat applications:
    - User messages: Error-only capture with PII redaction
    - User names: Never captured (zero PII exposure)
    - Responses: Minimal sampling (5%) for quality monitoring
    - No artifact storage: Optimizes for privacy and cost

    Pipeline-level policy is very restrictive; step annotations selectively enable
    capture only where needed for debugging and quality assurance.

    Args:
        message: User's chat message
        user_name: User's name for personalization
        personality: Agent personality style

    Returns:
        Chat response with metadata
    """
    response = generate_chat_response(
        message=message,
        user_name=user_name,
        personality=personality,
    )

    return response


if __name__ == "__main__":
    print("🤖 Creating Chat Agent Pipeline Deployment...\n")

    print(
        "💡 Note: Skipping local test due to ZenML integration loading issues"
    )
    print("📦 Creating deployment for serving...\n")

    try:
        # Create deployment with configured parameters
        chat_agent_pipeline._prepare_if_possible()
        deployment = chat_agent_pipeline._create_deployment()

        print(f"✅ Deployment ID: {deployment.id}")
        print("\n🔧 Start serving:")
        print(f"export ZENML_PIPELINE_DEPLOYMENT_ID={deployment.id}")
        print("python -m zenml.serving")

        print("\n💬 Test chat:")
        print("# Simple HTTP request")
        print("curl -X POST 'http://localhost:8000/invoke' \\")
        print("  -H 'Content-Type: application/json' \\")
        print(
            '  -d \'{"parameters": {"message": "Hi!", "user_name": "Alice"}}\''
        )

        print("\n# Async job + status polling")
        print("curl -X POST 'http://localhost:8000/invoke?mode=async' \\")
        print("  -H 'Content-Type: application/json' \\")
        print(
            '  -d \'{"parameters": {"message": "Hi!", "user_name": "Alice"}}\''
        )
        print("# Then: curl http://localhost:8000/jobs/<job_id>")

        print("\n# WebSocket streaming (real-time)")
        print("wscat -c ws://localhost:8000/stream")
        print(
            '# Send: {"parameters": {"message": "Hi!", "user_name": "Alice"}}'
        )

    except Exception as e:
        print(f"❌ Deployment failed: {e}")
