# ZenML Pipeline Serving - Simple Weather Agent Example

This example demonstrates how to serve a ZenML pipeline as a FastAPI endpoint that can accept runtime parameters.

## Files

1. `weather_pipeline.py` - A simple weather agent pipeline
2. `test_serving.py` - Test script to verify the serving endpoints
3. `README.md` - This guide

## Setup (Optional: For LLM Analysis)

To use real LLM analysis instead of rule-based fallback:

```bash
# Set your OpenAI API key
export OPENAI_API_KEY=your_openai_api_key_here

# Install OpenAI package
pip install openai
```

If no API key is provided, the pipeline will use an enhanced rule-based analysis as fallback.

## How to Run

### Step 1: Create a Pipeline Deployment

```bash
python weather_pipeline.py
```

This will:
- Create a pipeline deployment (NOT run it)
- Output a deployment ID like: `12345678-1234-5678-9abc-123456789abc`

**Note**: This uses ZenML's internal deployment creation mechanism as there's no public API to create deployments without running the pipeline.

### Step 2: Start the Serving Service

```bash
# Set the deployment ID from step 1
export ZENML_PIPELINE_DEPLOYMENT_ID=your_deployment_id_from_step_1

# Start the FastAPI serving service
python -m zenml.serving
```

The service will start on `http://localhost:8000`

### Step 3: Test the Endpoints

In another terminal:

```bash
python test_serving.py
```

Or test manually with curl:

```bash
# Get weather for Paris
curl -X POST "http://localhost:8000/invoke" \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"city": "Paris"}}'

# Get weather for Tokyo  
curl -X POST "http://localhost:8000/invoke" \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"city": "Tokyo"}}'
```

## Available Endpoints

- `GET /` - Service overview
- `GET /health` - Health check
- `GET /info` - Pipeline information
- `POST /invoke` - Execute pipeline with parameters
- `GET /metrics` - Execution statistics

## How It Works

1. **Pipeline Deployment**: The pipeline deployment is created without being executed
2. **Serving Service**: FastAPI app loads the deployment and makes it callable
3. **Runtime Parameters**: Each API call can pass different city names
4. **AI Agent Logic**: The pipeline analyzes weather and provides recommendations with LLM or rule-based fallback

## Key Points

- The pipeline deployment is created once but can be executed many times
- Each execution can have different parameters (different cities)
- The serving service handles parameter injection automatically
- Results are returned as JSON responses
- LLM analysis provides intelligent weather insights when OpenAI API key is available
- Rule-based fallback ensures the service works even without API keys