from agents import Agent


def get_city_info(city: str) -> str:
    """Provides a fun fact about a given city."""
    if "paris" in city.lower():
        return "Paris is known as the 'City of Light'."
    elif "tokyo" in city.lower():
        return "Tokyo is the most populous metropolitan area in the world."
    else:
        return f"Sorry, I don't have a fun fact for {city}."


# PanAgent's adapter will discover this 'agent' variable by convention.
agent = Agent(
    name="FactBot",
    instructions="You are a helpful assistant that provides fun facts about cities using your tools.",
    tools=[get_city_info],
    # model="gpt-5-nano" # The SDK defaults to a suitable model.
)
