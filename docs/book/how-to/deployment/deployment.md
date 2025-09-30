---
description: Deploy pipelines as HTTP services for real-time execution
icon: rocket-launch
---

# Pipeline Deployment

Pipeline deployment allows you to run ZenML pipelines as long-running HTTP services for real-time execution, rather than traditional batch mode execution. This enables you to invoke pipelines through HTTP requests and receive immediate responses.

## What is a Pipeline Deployment?

A pipeline deployment is a long-running HTTP server that wraps your pipeline in a web application, allowing it to be executed on-demand through HTTP requests. Unlike orchestrators that execute pipelines in batch mode, deployments create persistent services that can handle multiple concurrent pipeline executions.

When you deploy a pipeline, ZenML creates an HTTP server (called a **Deployment**) that can execute your pipeline multiple times in parallel by invoking HTTP endpoints.

## Common Use Cases

Pipeline deployments are ideal for scenarios requiring real-time, on-demand execution of ML workflows:

**Online ML Inference**: Deploy trained models as HTTP services for real-time predictions, such as fraud detection in payment systems, recommendation engines for e-commerce, or image classification APIs. Pipeline deployments handle feature preprocessing, model loading, and prediction logic while managing concurrent requests efficiently.

**LLM Agent Workflows**: Build intelligent agents that combine multiple AI capabilities like intent analysis, retrieval-augmented generation (RAG), and response synthesis. These deployments can power chatbots, customer support systems, or document analysis services that require multi-step reasoning and context retrieval.

**Real-time Data Processing**: Process streaming events or user interactions that require immediate analysis and response, such as real-time analytics dashboards, anomaly detection systems, or personalization engines.

**Multi-step Business Workflows**: Orchestrate complex processes involving multiple AI/ML components, like document processing pipelines that combine OCR, entity extraction, sentiment analysis, and classification into a single deployable service.

## How Deployments Work

To deploy a pipeline or snapshot, a **Deployer** stack component needs to be in your active stack:

```bash
zenml deployer register <DEPLOYER-NAME> --flavor=<DEPLOYER-FLAVOR>
zenml stack update -d <DEPLOYER-NAME>
```

The [**Deployer** stack component](../../component-guide/deployers/README.md) manages the deployment of pipelines as long-running HTTP servers. It integrates with a specific infrastructure back-end like Docker, AWS App Runner, GCP Cloud Run etc., in order to implement the following functionalities:

- Creating and managing persistent containerized services
- Exposing HTTP endpoints for pipeline invocation
- Managing the lifecycle of deployments (creation, updates, deletion)
- Providing connection information and management commands

{% hint style="info" %}
The **Deployer** and **Model Deployer** represent distinct stack components with slightly overlapping responsibilities. The **Deployer** component orchestrates the deployment of arbitrary pipelines as persistent HTTP services, while the **Model Deployer** component focuses exclusively on the deployment and management of ML models for real-time inference scenarios.

The **Deployer** component can easily accommodate ML model deployment through deploying ML inference pipelines. This approach provides enhanced flexibility for implementing custom business logic and preprocessing workflows around the deployed model artifacts. Conversely, specialized **Model Deployer** integrations may offer optimized deployment strategies, superior performance characteristics, and resource utilization efficiencies that exceed the capabilities of general-purpose pipeline deployments.

When deciding which component to use, consider the trade-offs between how much control you need over the deployment process and how much you want to offload to a particular integration specialized for ML model serving.
{% endhint %}

With a **Deployer** stack component in your active stack, a pipeline or snapshot can be deployed using the ZenML CLI:

```bash
# Deploy the pipeline `weather_pipeline` in the `weather_agent` module as a
# deployment named `my_deployment`
zenml pipeline deploy weather_agent.weather_pipeline --name my_deployment

# Deploy a snapshot named `weather_agent_snapshot` as a deployment named
# `my_deployment`
zenml pipeline snapshot deploy weather_agent_snapshot --deployment my_deployment
```

To deploy a pipeline using the ZenML SDK:

```python
from zenml.pipeline import pipeline

@pipeline
def weather_agent(city: str = "Paris", temperature: float = 20) -> str:
    return process_weather(city=city, temperature=temperature)

# Deploy the pipeline `weather_agent` as a deployment named `my_deployment`
deployment = weather_agent.deploy(deployment_name="my_deployment")
print(f"Deployment URL: {deployment.url}")
```

It is also possible to deploy snapshots programmatically:

```python
from zenml.client import Client

client = Client()
snapshot = client.get_snapshot(snapshot_name_or_id="weather_agent_snapshot")
# Deploy the snapshot `weather_agent_snapshot` as a deployment named
# `my_deployment`
deployment = client.provision_deployment(
    name_id_or_prefix="my_deployment",
    snapshot_id=snapshot.id,
)
print(f"Deployment URL: {deployment.url}")
```

Once deployed, a pipeline can be invoked through the URL exposed by the deployment. Every invocation of the deployment will create a new pipeline run.

The ZenML CLI provides a convenient command to invoke a deployment:

```bash
zenml deployment invoke my_deployment --city="London" --temperature=20
```

which is the equivalent of the following HTTP request:

```bash
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"city": "London", "temperature": 20}}'
```

## Deployment Lifecycle

Once a Deployment is created, it is tied to the specific **Deployer** stack component that was used to provision it and can be managed independently of the active stack as a standalone entity with its own lifecycle.

A Deployment contains the following key information:

- **`name`**: Unique deployment name within the project
- **`url`**: HTTP endpoint URL where the deployment can be accessed
- **`status`**: Current deployment status. This can take one of the following values `DeploymentStatus` enum values:
    - **`RUNNING`**: The deployment is running and accepting HTTP requests
    - **`ABSENT`**: The deployment is not currently provisioned
    - **`PENDING`**: The deployment is currently undergoing some operation (e.g. being created, updated or deleted)
    - **`ERROR`**: The deployment is in an error state. When in this state, more information about the error can be found in the ZenML logs, the Deployment `metadata` field or in the Deployment logs.
    - **`UNKNOWN`**: The deployment is in an unknown state
- **`metadata`**: Deployer-specific metadata describing the deployment's operational state

### Managing Deployments

To list all the deployments managed in your project by all the available Deployers:

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

Detailed information about a specific deployment can be obtained with the following command:

```bash
zenml deployment describe weather_agent
```

This provides comprehensive deployment details, including its state and access information:

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

{% hint style="info" %}
Additional information regarding the deployment can be shown with the same command:

* schema information about the deployment's input and output
* backend-specific metadata information about the deployment
* authentication information, if present
{% endhint %}

Deploying or redeploying a pipeline or snapshot on top of an existing deployment will update the deployment in place:

```bash
# Update the existing deployment named `my_deployment` with a new pipeline
# code version
zenml pipeline deploy weather_agent.weather_pipeline --name my_deployment --update

# Update the existing deployment named `my_deployment` with a new snapshot
# named `other_weather_agent_snapshot`
zenml deployment provision my_deployment --snapshot other_weather_agent_snapshot
```

{% hint style="warning" %}
**Deployment update checks and limitations**

- Updating a deployment owned by a different user requires additional confirmation. This is to avoid unintentionally updating someone else's deployment.
- An existing deployment cannot be updated using a stack different from the one it was originally deployed with.
- A pipeline snapshot can only have one deployment running at a time. You cannot deploy the same snapshot multiple times. You either have to delete the existing deployment and deploy the snapshot again or create a different snapshot.
{% endhint %}

Deprovisioning and deleting a deployment are two different operations. Deprovisioning a deployment keeps a record of it in the ZenML database so that it can be easily restored later if needed. Deleting a deployment completely removes it from the ZenML store:

```bash
# Deprovision the deployment named `my_deployment`
zenml deployment deprovision my_deployment

# Re-provision the deployment named `my_deployment` with the same configuration as before
zenml deployment provision my_deployment

# Deprovision and delete the deployment named `my_deployment`
zenml deployment delete my_deployment
```

{% hint style="warning" %}
**Deployer deletion**

A Deployer stack component cannot be deleted as long as there is at least one deployment managed by it that is not in an `ABSENT` state. To delete a Deployer stack component, you need to first deprovision or delete all the deployments managed by it. If some deployments are stuck in an `ERROR` state, you can use the `--force` flag to delete them without the need to deprovision them first, but be aware that this may leave some infrastructure resources orphaned.
{% endhint %}

The server logs of a deployment can be accessed with the following command:

```bash
zenml deployment logs my_deployment
```

## Deployable Pipeline Requirements

While any pipeline can technically be deployed, following these guidelines ensures practical usability:

### Pipeline Input Parameters

Pipelines should accept explicit parameters to enable dynamic invocation:

```python
@pipeline
def weather_agent(city: str = "Paris", temperature: float = 20) -> str:
    return process_weather(city=city, temperature=temperature)
```

{% hint style="info" %}
**Input Parameter Requirements:**

- All pipeline input parameters must have default values. This is a current limitation of the deployment mechanism.
- Input parameters must use JSON-serializable data types (`int`, `float`, `str`, `bool`, `list`, `dict`, `tuple`, Pydantic models). Other data types are not currently supported and will result in an error when deploying the pipeline.
- Pipeline input parameter names must match step parameter names. E.g. if the pipeline has an input parameter named `city` that is passed to a step input argument, that step argument must also be named `city`.
{% endhint %}


When deployed, the example pipeline above can be invoked:

* with a CLI command like the following:

```bash
zenml deployment invoke my_pipeline --city=Paris --temperature=20
```

* or with an HTTP request like the following:

```bash
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"city": "Paris", "temperature": 20}}'
```

{% hint style="warning" %}
Pipeline input parameters behave differently when pipelines are deployed than when they are run as a batch job. When running a parameterized pipeline, its input parameters are evaluated before the pipeline run even starts and can be used to configure the structure of the pipeline DAG. When invoking a deployment, the input parameters do not have an effect on the pipeline DAG structure, so a pipeline like the following will not work as expected:

```python
@pipeline
def switcher(
    mode: str = "analyze",
    city: str = "Paris",
    topic: str = "ML",
) -> str:
    return (
        analyze(city) if mode == "analyze" else generate(topic)
    )  # this will always use the "analyze" step when deploying the pipeline
```

{% endhint %}

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

{% hint style="info" %}
**Output Requirements:**

- Return values must be step outputs.
- Return values must be JSON-serializable (`int`, `float`, `str`, `bool`, `list`, `dict`, `tuple`, Pydantic models). Other data types are not currently supported and will result in an error when deploying the pipeline.
- The names of the step output artifacts determine the response structure (see example below)
- For clashing output names, the naming convention used to differentiate them is `<step_name>.<output_name>`
{% endhint %}

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

### Deployment Authentication

A rudimentary form of HTTP Basic authentication can be enabled for deployments by configuring one of two deployer configuration options:

* `generate_auth_key`: set to `True` to automatically generate a shared secret key for the deployment. This is not set by default.
* `auth_key`: configure the shared secret key manually.

```python
@pipeline(
    settings={
        "deployer": {
            "generate_auth_key": True,
        }
    }
)
def weather_agent(city: str = "Paris", temperature: float = 20) -> str:
    return process_weather(city=city, temperature=temperature)
```

Deploying the above pipeline automatically generates and returns a key that will be required in the `Authorization` header of HTTP requests made to the deployment:

```bash
curl -X POST http://localhost:8000/invoke \
  -H "Authorization: Bearer <GENERATED_AUTH_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"city": "Paris", "temperature": 20}}'
```

## Deployment Initialization, Cleanup and State

It often happens that the HTTP requests made to the same deployment share some type of initialization or cleanup or need to share the same global state or. For example:

* a machine learning model needs to be loaded in memory, initialized and then shared between all the HTTP requests made to the deployment in order to be used by the deployed pipeline to make predictions

* a database client must be initialized and shared across all the HTTP requests made to the deployment in order to read and write data

To achieve this, it is possible to configure custom initialization and cleanup hooks for the pipeline being deployed:

```python

def init_llm(model_name: str):
    # Initialize and store the LLM in memory when the deployment is started, to
    # be shared by all the HTTP requests made to the deployment
    return LLM(model_name=model_name)

def cleanup_llm(llm: LLM):
    # Cleanup the LLM when the deployment is stopped
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

This mechanism can be used to initialize and share global state between all the HTTP requests made to the deployment or to execute long-running initialization or cleanup operations when the deployment is started or stopped rather than on each HTTP request.

## Best Practices

1. **Design for Parameters**: Structure your pipelines to accept meaningful parameters that control behavior
2. **Provide Default Values**: Ensure all parameters have sensible defaults
3. **Return Useful Data**: Design pipeline outputs to provide meaningful responses
4. **Use Type Annotations**: Leverage Pydantic models for complex parameter types
5. **Use Global Initialization and State**: Use the `on_init` and `on_cleanup` hooks along with the `pipeline_state` step context property to initialize and share global state between all the HTTP requests made to the deployment. Also use these hooks to execute long-running initialization or cleanup operations when the deployment is started or stopped rather than on each HTTP request.
5. **Handle Errors Gracefully**: Implement proper error handling in your steps
6. **Test Locally First**: Validate your deployable pipeline locally before deploying to production

## Conclusion

Pipeline deployment transforms ZenML pipelines from batch processing workflows into real-time services. By following the guidelines for deployable pipelines and understanding the deployment lifecycle, you can create robust, scalable ML services that integrate seamlessly with web applications and real-time systems.

See also:
- [Steps & Pipelines](../steps-pipelines/steps_and_pipelines.md) - Core building blocks
- [Deployer Stack Component](../../component-guide/deployers/README.md) - The stack component that manages the deployment of pipelines as long-running HTTP servers