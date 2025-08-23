from crewai import Agent, Crew, Task
from crewai.tools import tool


@tool("Weather Checker Tool")
def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"Current weather in {city}: Sunny, 22°C (72°F), light breeze"


# Weather Specialist Agent
weather_checker = Agent(
    role="Weather Specialist",
    goal="Check weather conditions for a given city: {city}",
    backstory="You are a meteorology expert who provides accurate weather updates. When you get weather information, you immediately report it clearly.",
    tools=[get_weather],
    verbose=False,
    max_iter=2,
)


# Travel Advisor Agent
travel_advisor = Agent(
    role="Travel Advisor",
    goal="Give practical travel advice based on weather conditions for {city}",
    backstory="You are an experienced travel advisor who helps people prepare for their trips.",
    verbose=False,
    max_iter=2,
)


# Task 1: Check weather with parameterized city
check_weather_task = Task(
    description="Check the current weather in {city} and provide a weather report.",
    expected_output="A clear statement of the current weather conditions in {city} including temperature and conditions",
    agent=weather_checker,
)


# Task 2: Packing advice based on weather
packing_advice_task = Task(
    description="Based on the weather report for {city}, provide 3-5 specific items to pack for the trip.",
    expected_output="A list of 3-5 specific items to pack based on the weather conditions",
    agent=travel_advisor,
    context=[check_weather_task],
)


# PanAgent will discover this 'crew' variable
crew = Crew(
    agents=[weather_checker, travel_advisor],
    tasks=[check_weather_task, packing_advice_task],
    verbose=False,
)
