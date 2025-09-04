"""Weather Agent Pipeline with Simplified Capture Settings.

This pipeline demonstrates how to use ZenML's simplified capture settings
to control data logging and artifact persistence in a weather analysis service.

Key Capture Features:
- City names: Always captured (safe public data) - settings: {"inputs": {"city": "full"}}
- Weather data: Metadata-only (run tracking without payload exposure) - settings: {"inputs": {"weather_data": "metadata"}}
- LLM responses: Full capture with complete artifact persistence - settings: {"outputs": "full"}
- Pipeline default: Conservative metadata-only mode with custom redaction rules

This example shows the new simplified syntax for capture configuration with
fine-grained control over different data types.
"""

import os
import random
from typing import Dict

from zenml import pipeline, step
from zenml.config import DockerSettings

# Import enums for type-safe capture mode configuration
from zenml.config.docker_settings import PythonPackageInstaller
from zenml.deployers.serving.policy import CapturePolicyMode as CaptureMode
from zenml.steps.step_context import get_step_context

# Note: You can use either approach:
# 1. String literals: "full", "metadata", "sampled", "errors_only", "none"
# 2. Type-safe enums: CaptureMode.FULL, CaptureMode.METADATA, etc.
# 3. Capture constants: Capture.FULL, Capture.METADATA, etc.
# This example demonstrates the type-safe enum approach

docker_settings = DockerSettings(
    requirements=["openai"],
    environment={"OPENAI_API_KEY": os.getenv("OPENAI_API_KEY")},
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

            self.client = openai.OpenAI(api_key=api_key)
        except Exception as e:
            print(f"Error initializing OpenAI client: {e}")


def init_hook() -> PipelineState:
    """Initialize the pipeline."""
    print("Initializing the pipeline...")

    return PipelineState()


@step(
    settings={
        "serving_capture": {
            "inputs": {"city": CaptureMode.FULL},
            "outputs": CaptureMode.FULL,
        }
    }
)
def get_weather(city: str) -> Dict[str, float]:
    """Simulate getting weather data for a city.

    Demonstrates:
    - Input capture: City names are safe to log for monitoring
    - Output capture: Weather data is valuable for debugging and analytics
    """
    # In real life, this would call a weather API
    # For demo, we generate based on city name
    temp_base = sum(ord(c) for c in city.lower()) % 30
    return {
        "temperature": temp_base + random.uniform(-5, 5),
        "humidity": 40 + (ord(city[0]) % 40),
        "wind_speed": 5 + (len(city) % 15),
    }


@step(
    settings={
        "serving_capture": {
            "inputs": {
                "weather_data": CaptureMode.METADATA,
                "city": CaptureMode.FULL,
            },
            "outputs": CaptureMode.FULL,
        }
    }
)
def analyze_weather_with_llm(weather_data: Dict[str, float], city: str) -> str:
    """Use LLM to analyze weather and provide intelligent recommendations.

    Demonstrates:
    - Input capture: Weather data uses metadata-only (run records but no payload preview)
    - Input capture: City names are always captured for monitoring
    - Output capture: Full capture of all responses for complete monitoring
    - Artifacts: Always persist LLM responses for analysis and debugging
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
        client = pipeline_state.client

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
    on_init=init_hook,
    settings={
        "docker": docker_settings,
        # Pipeline-level defaults using new simplified syntax with type-safe enums
        "serving_capture": {
            "mode": CaptureMode.NONE,  # "mode": CaptureMode.FULL,  # Type-safe enum value
            "max_bytes": 32768,  # Increased for better artifact storage
            "redact": ["password", "token", "key", "secret", "api_key"],
        },
        "deployer.gcp": {
            "allow_unauthenticated": True,
            # "location": "us-central1",
            "min_instances": 0,
            "generate_auth_key": True,
        },
    },
)
def weather_agent_pipeline(city: str = "London") -> str:
    """Weather agent pipeline demonstrating step-level capture annotations.

    Uses LLM to provide intelligent weather analysis with full artifact persistence:
    - City names: Always captured (safe public data)
    - Weather data: Metadata-only logging (structured data, not sensitive)
    - LLM responses: Full capture with complete artifact storage for analysis

    Args:
        city: City name to analyze weather for

    Returns:
        LLM-powered weather analysis and recommendations
    """
    weather_data = get_weather(city=city)
    result = analyze_weather_with_llm(weather_data=weather_data, city=city)
    return result


if __name__ == "__main__":
    # Create a deployment (not run it!)
    # We need to access the private _create_deployment method because
    # ZenML doesn't have a public method to create deployments without running

    # First prepare the pipeline
    weather_agent_pipeline._prepare_if_possible()

    # Create deployment without running
    deployment = weather_agent_pipeline._create_deployment()

    print("\n✅ Pipeline deployed!")
    print(f"📋 Deployment ID: {deployment.id}")
    print("\n🚀 To serve this pipeline:")
    print(f"   export ZENML_PIPELINE_DEPLOYMENT_ID={deployment.id}")
    print("   python -m zenml.deployers.serving")
