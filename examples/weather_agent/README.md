## Weather Agent Pipeline

This example shows how to:

- Create a weather analysis pipeline using ZenML
- Analyze weather data with LLM-powered recommendations
- Use rule-based fallback when LLM is unavailable
- Deploy for production serving with millisecond latency

The weather agent pipeline takes a city name as input and provides comprehensive weather analysis including current conditions, comfort ratings, activity recommendations, and clothing suggestions. It can run with a real LLM (via OpenAI) if API keys are available, or fall back to intelligent rule-based analysis for offline demos.

### Why pipelines (for ML and AI engineers)

- Reproducible & portable: versioned steps and artifacts that run locally or on the cloud without code changes
- Unified for models and agents: the same primitives work for scikit-learn and LLM/agent workflows
- Evaluate & observe by default: step metadata (tokens, latency), lineage, and quality reports are first-class

Modeling agents as pipelines makes non-deterministic systems shippable: prompts, tools, and routing become explicit steps; outputs become versioned artifacts you can evaluate and compare. The same development and production practices you trust for classical ML apply 1:1 to agent workflows.

### What's Included

- **Weather Analysis Pipeline**: `weather_agent_pipeline` that fetches weather data and provides intelligent analysis
- **LLM Integration**: OpenAI GPT-3.5-turbo for enhanced weather recommendations
- **Rule-based Fallback**: Deterministic analysis when LLM is unavailable
- **Production Ready**: Optimized for serving with millisecond response times

### Prerequisites

```bash
pip install "zenml[server]"
zenml init
```

Optional for LLM analysis:

```bash
# OpenAI API key for enhanced recommendations
export OPENAI_API_KEY="your-key"
```

### Get the example & install dependencies

If you don't have this repository locally yet:

```bash
git clone --depth 1 https://github.com/zenml-io/zenml.git
cd zenml/examples/weather_agent
```

Then install example dependencies:

```bash
pip install openai  # Optional for LLM analysis
```

### Run the pipeline in batch mode

```bash
python run.py
```

Enter a city name when prompted to get weather analysis:

```
Enter city to get weather recommendations: Paris
```

The pipeline will:
1. Fetch simulated weather data for the city
2. Analyze conditions using LLM (if available) or rule-based logic
3. Provide recommendations for activities, clothing, and comfort ratings

Example output with LLM:

```
🤖 LLM Weather Analysis for Paris:

Assessment: Pleasant weather conditions with moderate temperatures
Comfort Level: 8/10
Current conditions show 22°C with 65% humidity and light winds

Recommended Activities: Perfect for outdoor dining, walking tours, visiting parks
What to Wear: Light jacket or sweater, comfortable walking shoes
Weather Tips: Ideal conditions for sightseeing and outdoor activities

---
Raw Data: 22.3°C, 65% humidity, 8.2 km/h wind
Powered by: OpenAI GPT-3.5-turbo
```

Example output with fallback:

```
🤖 Weather Analysis for Paris:

Assessment: Pleasant weather with 65% humidity
Comfort Level: 8/10
Wind Conditions: 8.2 km/h

Recommended Activities: hiking, cycling, outdoor dining
What to Wear: light jacket or sweater
Weather Tips: Perfect weather for outdoor activities!

---
Raw Data: 22.3°C, 65% humidity, 8.2 km/h wind
Analysis: Rule-based AI (LLM unavailable)
```

#### View results

```bash
zenml login --local  # Start ZenML dashboard locally
```

Open the ZenML dashboard to see:
- **Weather Analysis Pipeline**: Processing traces with city inputs and weather analysis outputs
- **Step Artifacts**: Weather data and analysis results stored as versioned artifacts
- **Pipeline Runs**: Complete execution history with metadata and performance metrics

#### Analysis Features

The weather analysis pipeline provides:

1. **Weather Data Simulation**: Temperature, humidity, and wind speed based on city characteristics
2. **LLM Analysis**: Intelligent recommendations using OpenAI GPT-3.5-turbo
3. **Rule-based Fallback**: Deterministic analysis covering temperature ranges, humidity, and wind conditions
4. **Comfort Scoring**: Quantitative comfort assessment (1-10 scale)
5. **Activity Recommendations**: Contextual suggestions based on weather conditions
6. **Clothing Advice**: Appropriate attire recommendations for current conditions

### Deploy the pipeline for real-time execution

The pipeline is optimized for deployment:

- **Run-only mode**: Millisecond latency with zero database writes
- **In-memory handoff**: Direct step output passing without filesystem operations
- **Scalable**: Supports multiple workers and high concurrency
- **Cloud ready**: Configured for GCP and AWS deployment

To deploy the pipeline for real-time execution, you need a **Deployer** stack component in your stack. Luckily, the `default` stack
comes with a built-in local deployer:

```bash
zenml stack set default
```

Then you can deploy the pipeline with:

```bash
zenml pipeline deploy pipelines.weather_agent
```

The pipeline will be deployed in a background process and expose an HTTP endpoint at e.g. `http://localhost:8000`.

You can then send HTTP requests to the endpoint to trigger pipeline runs using either `zenml pipeline invoke` or `curl`:

```bash
zenml deployment invoke weather_agent --city=Paris
```

Or:

```bash
curl -X POST http://localhost:8000/invoke \
  -H 'Content-Type: application/json' \
  -d '{
        "parameters": {
          "city": "Paris"
        }
      }'
```

The response will be the output of the last step of the pipeline run. Every invocation is a new pipeline run that can be inspected and managed in the ZenML dashboard.


#### Cleanup

You can manage and cleanup your running deployments e.g. with:

```bash
zenml deployment list
zenml deployment delete weather_agent
```

### Structure

```
examples/weather_agent/
├── pipelines/
│   ├── __init__.py
│   ├── hooks.py                 # Pipeline state and OpenAI client initialization
│   └── weather_agent.py         # Weather analysis pipeline definition
├── steps/
│   ├── __init__.py
│   └── weather_agent.py         # Weather data fetching and LLM analysis steps
├── run.py                       # CLI runner for the pipeline
└── README.md                    # This file
```

### Use Cases

This weather agent pipeline is ideal for:

- **Travel Planning**: Quick weather assessments for destination planning
- **Activity Recommendations**: Context-aware suggestions based on conditions
- **Clothing Advice**: Automated wardrobe recommendations
- **Weather APIs**: Backend service for weather-aware applications
- **Batch Processing**: Analyzing weather for multiple cities

### Notes

- Weather data is simulated based on city name characteristics for demo purposes
- The pipeline gracefully falls back to rule-based analysis when OpenAI API is unavailable
- Analysis results include both LLM insights and raw weather data for transparency
- For production deployments, consider using real weather APIs for current conditions