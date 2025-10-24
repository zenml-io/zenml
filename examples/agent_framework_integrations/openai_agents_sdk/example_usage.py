#!/usr/bin/env python3
"""Example usage of the OpenAI Agents SDK agent."""

import os

from agents import Runner
from openai_agent import agent


def main():
    """Run a simple example with the OpenAI Agents SDK agent."""
    # Check if API key is available
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable is not set")
        print(
            "Please set your OpenAI API key: export OPENAI_API_KEY='your-key-here'"
        )
        return

    print("🤖 OpenAI Agents SDK Example")
    print("=" * 40)

    # Example queries to test the agent
    queries = [
        "What's the weather like in Tokyo?",
        "Tell me about Paris",
        "What's the weather in London and give me some facts about the city?",
    ]

    for query in queries:
        print(f"\n📝 Query: {query}")
        print("🔄 Processing...")

        try:
            # Run the agent synchronously
            result = Runner.run_sync(agent, query)

            # Print the response
            print(f"🤖 Response: {result.final_output}")

        except Exception as e:
            print(f"❌ Error: {str(e)}")

        print("-" * 40)


if __name__ == "__main__":
    main()
