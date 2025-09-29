---
description: Deploy pipelines as HTTP services for real-time execution
---

# Pipeline Deployment

Pipeline deployment allows you to run ZenML pipelines as long-running HTTP services for real-time execution, rather than traditional batch mode execution. This enables you to invoke pipelines through HTTP requests and receive immediate responses.

## What is a Pipeline Deployment?

A pipeline deployment is a long-running HTTP server that wraps your pipeline in a web application, allowing it to be executed on-demand through HTTP requests. Unlike orchestrators that execute pipelines in batch mode, deployments create persistent services that can handle multiple concurrent pipeline executions.

When you deploy a pipeline, ZenML creates an HTTP server (called a Deployment) that can execute your pipeline multiple times in parallel by invoking HTTP endpoints.

## How Deployments Work

A **Deployer** is a stack component that manages the deployment of pipelines as long-running HTTP servers. The deployer handles:

- Creating and managing persistent containerized services
- Exposing HTTP endpoints for pipeline invocation
- Managing the lifecycle of deployments (creation, updates, deletion)
- Providing connection information and management commands

## Creating Deployments

### Using the CLI

Deploy a pipeline or snapshot using the ZenML CLI:

```bash
# Deploy a pipeline
zenml pipeline deploy weather_agent.weather_pipeline --name my_deployment

# Deploy a snapshot
zenml pipeline snapshot deploy weather_agent_snapshot --deployment my_deployment
```

### Using the SDK

Deploy directly from your Python code:

```python
from zenml.pipeline import pipeline

@pipeline
def weather_agent(city: str = "Paris", temperature: float = 20) -> str:
    return process_weather(city=city, temperature=temperature)

# Deploy the pipeline
deployment = weather_agent.deploy(deployment_name="my_deployment")
print(f"Deployment URL: {deployment.url}")
```

You can also deploy snapshots programmatically:

```python
from zenml.client import Client

client = Client()
snapshot = client.get_snapshot(snapshot_name_or_id="weather_agent_snapshot")
deployment = client.provision_deployment(
    name_id_or_prefix="my_deployment",
    snapshot_id=snapshot.id,
)
print(f"Deployment URL: {deployment.url}")
```

## Deployment Lifecycle

A deployment contains the following key information:

- **`name`**: Unique deployment name within the project
- **`url`**: HTTP endpoint URL for the deployment
- **`status`**: Current deployment status (RUNNING, STOPPED, etc.)
- **`metadata`**: Deployer-specific metadata and configuration

### Managing Deployments

List all deployments:

```bash
zenml deployment list
```

This shows a table with deployment details:

```
╭──────────────────────┬────────────────────────┬──────────────────────┬───────────────────────┬───────────┬─────────────────┬─────────────────╮
│         NAME         │ PIPELINE               │ SNAPSHOT             │ URL                   │ STATUS    │ STACK           │ OWNER           │
├──────────────────────┼────────────────────────┼──────────────────────┼───────────────────────┼───────────┼─────────────────┼─────────────────┤
│  zenpulse-endpoint   │ zenpulse_agent         │                      │ http://localhost:8000 │ ⚙ RUNNING │ aws-stack       │ hamza@zenml.io  │
├──────────────────────┼────────────────────────┼──────────────────────┼───────────────────────┼───────────┼─────────────────┼─────────────────┤
│ docker-weather-agent │ weather_agent_pipeline │ docker-weather-agent │ http://localhost:8000 │ ⚙ RUNNING │ docker-deployer │ stefan@zenml.io │
├──────────────────────┼────────────────────────┼──────────────────────┼───────────────────────┼───────────┼─────────────────┼─────────────────┤
│    weather_agent     │ weather_agent          │                      │ http://localhost:8001 │ ⚙ RUNNING │ docker-deployer │ stefan@zenml.io │
╰──────────────────────┴────────────────────────┴──────────────────────┴───────────────────────┴───────────┴─────────────────┴─────────────────╯
```

Get detailed deployment information:

```bash
zenml deployment describe weather_agent
```

This provides comprehensive deployment details:

```
🚀 Deployment: weather_agent is: RUNNING ⚙

Pipeline: weather_agent
Snapshot: 0866c821-d73f-456d-a98d-9aa82f41282e
Stack: docker-deployer

📡 Connection Information:

Endpoint URL: http://localhost:8001
Swagger URL: http://localhost:8001/docs
CLI Command Example:
  zenml deployment invoke weather_agent --city="London"

cURL Example:
  curl -X POST http://localhost:8001/invoke \
    -H "Content-Type: application/json" \
    -d '{
      "parameters": {
        "city": "London"
      }
    }'

⚙️  Management Commands
╭────────────────────────────────────────────┬─────────────────────────────────────────────────────╮
│ zenml deployment logs weather_agent -f     │ Follow deployment logs in real-time                 │
│ zenml deployment describe weather_agent    │ Show detailed deployment information                │
│ zenml deployment deprovision weather_agent │ Deprovision this deployment and keep a record of it │
│ zenml deployment delete weather_agent      │ Deprovision and delete this deployment              │
╰────────────────────────────────────────────┴─────────────────────────────────────────────────────╯
```

Deploying or redeploying a pipeline or snapshot over an existing deployment will update the deployment in place:

```bash
# Update existing deployment with new pipeline version
zenml pipeline deploy weather_agent.weather_pipeline --name my_deployment --update
```

Deprovision and remove a deployment completely:

```bash
zenml deployment delete weather_agent
```

This will prompt for confirmation and then deprovision and delete the deployment.

### Constraints and Limitations

- A deployment cannot be updated to use a different stack
- A pipeline snapshot can only have one deployment running at a time
- For security reasons, updating a deployment belonging to a different user requires the `--overtake` flag

## Deployable Pipeline Requirements

While any pipeline can technically be deployed, following these guidelines ensures practical usability:

### Pipeline Parameters

Pipelines should accept explicit parameters to enable dynamic invocation:

```python
@pipeline
def weather_agent(city: str = "Paris", temperature: float = 20) -> str:
    return process_weather(city=city, temperature=temperature)
```

**Parameter Requirements:**
- Must have default values
- Must use JSON-serializable data types (`int`, `float`, `str`, `bool`, `list`, `dict`, `tuple`, Pydantic models)
- Parameter names must match step input names

When deployed, the example pipeline above can be invoked:

* with the following CLI command:

```bash
zenml deployment invoke my_pipeline --city=Paris --temperature=20
```

* or with the following HTTP request:

```bash
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"city": "Paris", "temperature": 20}}'
```

### Pipeline Outputs

Pipelines should return meaningful values for useful HTTP responses:

```python
@step
def process_weather(city: str, temperature: float) -> Annotated[str, "weather_analysis"]:
    return f"The weather in {city} is {temperature} degrees Celsius."

@pipeline
def weather_agent(city: str = "Paris", temperature: float = 20) -> str:
    weather_analysis = process_weather(city=city, temperature=temperature)
    return weather_analysis
```

**Output Requirements:**
- Return values must be JSON-serializable
- Output artifact names determine the response structure
- For clashing output names, the convention used to differentiate them is `<step_name>.<output_name>`

Invoking a deployment of this pipeline will return the response below. Note how the `outputs` field contains the value returned by the `process_weather` step and the name of the output artifact is used as the key.

```json
{
    "success": true,
    "outputs": {
        "weather_analysis": "The weather in Utopia is 25 degrees Celsius"
    },
    "execution_time": 8.160255432128906,
    "metadata": {
        "deployment_id": "e0b34be2-d743-4686-a45b-c12e81627bbe",
        "deployment_name": "weather_agent",
        "snapshot_id": "0866c821-d73f-456d-a98d-9aa82f41282e",
        "snapshot_name": null,
        "pipeline_name": "weather_agent",
        "run_id": "f2e9a3a7-afa3-459e-a970-8558358cf1fb",
        "run_name": "weather_agent-2025_09_29-14_09_55_726165",
        "parameters_used": {
            "city": "Utopia",
            "temperature": 25
        }
    },
    "error": null
}
```

### Deployment Initialization, Cleanup and State

It often happens that the HTTP requests made to the same deployment share some type of initialization or cleanup or need to share the same global state or. For example:

* a machine learning model needs to be loaded in memory, initialized and then shared between all the HTTP requests made to the deployment in order to be used by the deployed pipeline to make predictions

* a database client must be initialized and shared across all the HTTP requests made to the deployment in order to read and write data

To achieve this, you can configure custom initialization and cleanup hooks for the pipeline being deployed:

```python

def init_llm(model_name: str):
    return LLM(model_name=model_name)

def cleanup_llm(llm: LLM):
    llm.cleanup()

@step
def process_weather(city: str, temperature: float) -> Annotated[str, "weather_analysis"]:
    step_context = get_step_context()
    # The value returned by the on_init hook is stored in the pipeline state
    llm = step_context.pipeline_state
    return generate_llm_response(llm, city, temperature)

@pipeline(
    on_init=init_llm,
    on_cleanup=cleanup_llm,
)
def weather_agent(city: str = "Paris", temperature: float = 20) -> str:
    return process_weather(city=city, temperature=temperature)

weather_agent_deployment = weather_agent.with_options(
    on_init_kwargs={"model_name": "gpt-4o"},
).deploy(deployment_name="my_deployment")
```

The following happens when the pipeline is deployed and then later invoked:

1. The on_init hook is executed only once, when the deployment is started
2. The value returned by the on_init hook is stored in memory in the deployment and can be accessed by pipeline steps using the `pipeline_state` property of the step context
3. The on_cleanup hook is executed only once, when the deployment is stopped

This mechanism can be used to initialize and share global state between all the HTTP requests made to the deployment.

## Best Practices

1. **Design for Parameters**: Structure your pipelines to accept meaningful parameters that control behavior
2. **Provide Default Values**: Ensure all parameters have sensible defaults
3. **Return Useful Data**: Design pipeline outputs to provide meaningful responses
4. **Use Type Annotations**: Leverage Pydantic models for complex parameter types
5. **Use Global State**: Use the `on_init` and `on_cleanup` hooks along with the `pipeline_state` step context property to initialize and share global state between all the HTTP requests made to the deployment
5. **Handle Errors Gracefully**: Implement proper error handling in your steps
6. **Test Locally First**: Validate your deployable pipeline locally before deploying to production

## Conclusion

Pipeline deployment transforms ZenML pipelines from batch processing workflows into real-time services. By following the guidelines for deployable pipelines and understanding the deployment lifecycle, you can create robust, scalable ML services that integrate seamlessly with web applications and real-time systems.

See also:
- [Steps & Pipelines](./steps_and_pipelines.md) - Core building blocks
- [Configuration](./configuration.md) - Pipeline configuration options
- [Advanced Features](./advanced_features.md) - Advanced pipeline capabilities