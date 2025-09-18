"""Weather Agent Pipeline."""

import os
import random
from typing import Annotated, Dict

from zenml import pipeline, step
from zenml.client import Client
from zenml.config import DockerSettings

# Import enums for type-safe capture mode configuration
from zenml.config.docker_settings import PythonPackageInstaller
from zenml.config.resource_settings import ResourceSettings
from zenml.steps.step_context import get_step_context

docker_settings = DockerSettings(
    requirements=["openai"],
    prevent_build_reuse=True,
    python_package_installer=PythonPackageInstaller.UV,
)


class PipelineState:
    """Pipeline state."""

    def __init__(self) -> None:
        """Initialize the pipeline state."""
        self.openai_client = None

        try:
            # Try to use OpenAI API if available
            import os

            try:
                import openai
            except ImportError:
                raise ImportError("OpenAI package not available")

            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ImportError("OpenAI API key not found")

            self.openai_client = openai.OpenAI(api_key=api_key)
        except Exception as e:
            print(f"Error initializing OpenAI client: {e}")


def init_hook() -> PipelineState:
    """Initialize the pipeline."""
    print("Initializing the pipeline...")

    return PipelineState()


@step
def get_weather(city: str) -> Annotated[Dict[str, float], "weather_data"]:
    """Simulate getting weather data for a city.

    In run-only mode, this executes with millisecond latency and
    no persistence overhead.
    """
    # In real life, this would call a weather API
    # For demo, we generate based on city name
    temp_base = sum(ord(c) for c in city.lower()) % 30
    return {
        "temperature": temp_base + random.uniform(-5, 5),
        "humidity": 40 + (ord(city[0]) % 40),
        "wind_speed": 5 + (len(city) % 15),
    }


@step
def analyze_weather_with_llm(
    weather_data: Dict[str, float], city: str
) -> Annotated[str, "weather_analysis"]:
    """Use LLM to analyze weather and provide intelligent recommendations.

    In run-only mode, this step receives weather data via in-memory handoff
    and returns analysis with no database or filesystem writes.
    """
    temp = weather_data["temperature"]
    humidity = weather_data["humidity"]
    wind = weather_data["wind_speed"]

    step_context = get_step_context()
    pipeline_state = step_context.pipeline_state

    client = None
    if pipeline_state:
        assert isinstance(pipeline_state, PipelineState), (
            "Pipeline state is not a PipelineState"
        )
        client = pipeline_state.openai_client

    if client:
        # Create a prompt for the LLM
        weather_prompt = f"""You are a weather expert AI assistant. Analyze the following weather data for {city} and provide detailed insights and recommendations.

Weather Data:
- City: {city}
- Temperature: {temp:.1f}°C
- Humidity: {humidity}%
- Wind Speed: {wind:.1f} km/h

Please provide:
1. A brief weather assessment
2. Comfort level rating (1-10)
3. Recommended activities
4. What to wear
5. Any weather warnings or tips

Keep your response concise but informative."""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful weather analysis expert.",
                },
                {"role": "user", "content": weather_prompt},
            ],
            max_tokens=300,
            temperature=0.7,
        )

        llm_analysis = response.choices[0].message.content

        return f"""🤖 LLM Weather Analysis for {city}:

{llm_analysis}

---
Raw Data: {temp:.1f}°C, {humidity}% humidity, {wind:.1f} km/h wind
Powered by: OpenAI GPT-3.5-turbo"""

    else:
        # Fallback to rule-based analysis if LLM fails
        print("LLM not available, using fallback...")

        # Enhanced rule-based analysis
        if temp < 0:
            temp_desc = "freezing"
            comfort = 2
            activities = "indoor activities, ice skating"
            clothing = "heavy winter coat, gloves, warm boots"
            warning = "⚠️ Risk of frostbite - limit outdoor exposure"
        elif temp < 10:
            temp_desc = "cold"
            comfort = 4
            activities = "brisk walks, winter sports"
            clothing = "warm jacket, layers, closed shoes"
            warning = "Bundle up to stay warm"
        elif temp < 25:
            temp_desc = "pleasant"
            comfort = 8
            activities = "hiking, cycling, outdoor dining"
            clothing = "light jacket or sweater"
            warning = "Perfect weather for outdoor activities!"
        elif temp < 35:
            temp_desc = "hot"
            comfort = 6
            activities = "swimming, early morning walks"
            clothing = "light clothing, sun hat, sunscreen"
            warning = "Stay hydrated and seek shade"
        else:
            temp_desc = "extremely hot"
            comfort = 3
            activities = "indoor activities, swimming"
            clothing = "minimal light clothing, sun protection"
            warning = "⚠️ Heat warning - avoid prolonged sun exposure"

        # Humidity adjustments
        if humidity > 80:
            comfort -= 1
            warning += " High humidity will make it feel warmer."
        elif humidity < 30:
            warning += " Low humidity may cause dry skin."

        # Wind adjustments
        if wind > 20:
            warning += " Strong winds - secure loose items."

        return f"""🤖 Weather Analysis for {city}:

Assessment: {temp_desc.title()} weather with {humidity}% humidity
Comfort Level: {comfort}/10
Wind Conditions: {wind:.1f} km/h

Recommended Activities: {activities}
What to Wear: {clothing}
Weather Tips: {warning}

---
Raw Data: {temp:.1f}°C, {humidity}% humidity, {wind:.1f} km/h wind
Analysis: Rule-based AI (LLM unavailable)"""


@pipeline(
    enable_cache=False,
    on_init=init_hook,
    settings={
        "docker": docker_settings,
        "deployer.gcp": {
            "allow_unauthenticated": True,
            # "location": "us-central1",
            "generate_auth_key": True,
        },
        "deployer.aws": {
            "generate_auth_key": True,
        },
        "resources": ResourceSettings(
            memory="1GB",
            cpu_count=1,
            min_replicas=1,
            max_replicas=5,
            max_concurrency=10,
        ),
    },
    environment={"OPENAI_API_KEY": os.getenv("OPENAI_API_KEY")},
)
def weather_agent_pipeline(
    city: str = "London",
) -> str:
    """Weather agent pipeline optimized for run-only serving.

    Automatically uses run-only architecture for millisecond-class latency:
    - Zero database writes
    - Zero filesystem operations
    - In-memory step output handoff
    - Perfect for real-time inference

    Args:
        city: City name to analyze weather for

    Returns:
        LLM-powered weather analysis and recommendations
    """
    weather_data = get_weather(city=city)
    result = analyze_weather_with_llm(weather_data=weather_data, city=city)
    return result


if __name__ == "__main__":
    # First prepare the pipeline

    client = Client()

    data_input = input("Enter city to get weather: ")
    run = weather_agent_pipeline(city=data_input)

    # Load and print the output of the last step of the last run
    run = client.get_pipeline_run(run.id)
    result = run.steps["analyze_weather_with_llm"].output.load()
    print(result)
