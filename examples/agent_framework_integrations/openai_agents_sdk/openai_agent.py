"""OpenAI Agents SDK example for ZenML integration."""

from agents import Agent, function_tool


@function_tool
def get_weather(city: str) -> str:
    """Get weather information for a given city.

    Args:
        city: The name of the city to get weather for

    Returns:
        A string describing the weather conditions
    """
    return (
        f"It's always sunny in {city}! Temperature is 72°F with clear skies."
    )


@function_tool
def get_city_info(city: str) -> str:
    """Get general information about a city.

    Args:
        city: The name of the city to get information about

    Returns:
        A string with interesting facts about the city
    """
    city_facts = {
        "tokyo": "Tokyo is the capital of Japan and one of the world's most populous cities, known for its mix of traditional and modern culture.",
        "paris": "Paris is the capital of France, famous for the Eiffel Tower, art museums, and cuisine.",
        "new york": "New York City is the most populous city in the United States, known for its skyline, culture, and diversity.",
        "london": "London is the capital of England and the United Kingdom, famous for its history, architecture, and royal heritage.",
        "munich": "Munich is the capital of Bavaria, Germany's third-largest city, famous for Oktoberfest, beer gardens, BMW headquarters, and its proximity to the Alps.",
    }

    city_lower = city.lower()
    if city_lower in city_facts:
        return city_facts[city_lower]
    else:
        return f"{city} is a wonderful place to visit with its own unique culture and attractions!"


# Create the agent with function tools
agent = Agent(
    name="Travel Assistant",
    instructions="""You are a helpful travel assistant. You can provide weather information
    and general facts about cities around the world. When users ask about cities, use your
    available tools to get specific information. Be friendly and informative in your responses.""",
    model="gpt-5-nano",
    tools=[get_weather, get_city_info],
)
