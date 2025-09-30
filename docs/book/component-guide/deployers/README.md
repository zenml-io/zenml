---
description: Deploy pipelines as HTTP services for real-time execution
icon: rocket-launch
---

# Deployers

Pipeline deployment is the process of making ZenML pipelines available as long-running HTTP services for real-time execution. Unlike traditional batch execution through orchestrators, deployers create persistent web services that can handle on-demand pipeline invocations through HTTP requests.

Deployers are stack components responsible for managing the deployment of pipelines as containerized HTTP services that expose REST APIs for pipeline execution.

A deployed pipeline becomes a web service that can be invoked multiple times in parallel, receiving parameters through HTTP requests and returning pipeline outputs as JSON responses. This enables real-time inference, interactive workflows, and integration with web applications.

### When to use it?

Deployers are optional components in the ZenML stack. They are useful in the following scenarios:

- **Real-time Pipeline Execution**: Execute pipelines on-demand through HTTP requests rather than scheduled batch runs
- **Interactive Workflows**: Build applications that need immediate pipeline responses
- **API Integration**: Expose ML workflows as REST APIs for web applications or microservices
- **Real-time Inference**: Serve ML models through pipeline-based inference workflows
- **Agent-based Systems**: Create AI agents that execute pipelines in response to external events

Use deployers when you need request-response patterns, and orchestrators for scheduled, batch, or long-running workflows.

### Deployer Flavors

ZenML provides deployer implementations for different deployment environments:

| Deployer                           | Flavor    | Integration   | Notes                                                                        |
|------------------------------------|-----------|---------------|------------------------------------------------------------------------------|
| [Docker](docker.md)                | `docker`   | Built-in      | Deploys pipelines as locally running Docker containers                                |
| [GCP Cloud Run](gcp.md)            | `gcp`     | `gcp`         | Deploys pipelines to Google Cloud Run for serverless execution             |
| [AWS App Runner](aws.md)           | `aws`     | `aws`         | Deploys pipelines to AWS App Runner for serverless execution                       |
| [Custom Implementation](custom.md) | _custom_  |               | Extend the Deployer abstraction and provide your own implementation         |

If you would like to see the available flavors of deployers, you can use the command:

```shell
zenml deployer flavor list
```

### How to use it

You don't need to directly interact with the ZenML deployer stack component in your code. As long as the deployer that you want to use is part of your active [ZenML stack](../../user-guide/production-guide/understand-stacks.md), you can simply deploy a pipeline or snapshot using the ZenML CLI or the ZenML SDK.

Example:

* set up a stack with a deployer

```bash
zenml deployer register docker --flavor=local
zenml stack register docker_deployment -a default -o default -D docker --set
```

* deploy a pipeline or snapshot

```python
from zenml import pipeline


@pipeline
def my_pipeline(...) -> ...:
    ...
```

#### Specifying deployment resources

If your steps require additional hardware resources, you can specify them on your steps as described [here](https://docs.zenml.io/user-guides/tutorial/distributed-training/).

* **Pipeline Service Management**: Facilitates the deployment of ZenML pipelines as long-running HTTP services to various platforms such as local Docker, Kubernetes clusters, or cloud serverless platforms. The deployer holds all the stack-related configuration attributes required to interact with the deployment platform (e.g. cluster contexts, namespaces, authentication credentials, and resource specifications). The following are examples of configuring deployers and registering them as stack components:

   ```bash
   # Local Docker deployment
   zenml deployer register local_docker --flavor=local
   zenml stack register local_deployment -m default -a default -o default -d local_docker --set
   ```

   ```bash
   # Kubernetes deployment
   zenml integration install kubernetes
   zenml deployer register k8s_deployer --flavor=k8s \
   --kubernetes_context=production-cluster --kubernetes_namespace=zenml-deployments
   zenml stack register k8s_deployment -m default -a aws -o default -d k8s_deployer
   ```

* **Deployment Lifecycle Management**: Provides mechanisms for comprehensive lifecycle management of pipeline deployments, including the ability to create, update, start, stop, and delete pipeline services. This optimizes resource utilization and facilitates continuous delivery of pipeline updates. Core methods for interacting with pipeline deployments include:
  - `deploy_pipeline` - Deploys a pipeline or snapshot as an HTTP service and returns a Deployment object
  - `find_deployments` - Finds and returns a list of Deployment objects representing active pipeline services
  - `get_deployment` - Retrieves a specific deployment by name or ID
  - `update_deployment` - Updates an existing deployment with a new pipeline version
  - `delete_deployment` - Removes a deployment and cleans up associated resources

{% hint style="info" %}
ZenML uses the Deployment object to represent a pipeline service that has been deployed to a serving environment. The Deployment object is saved in the database and contains information about the deployment configuration, status, and connection details. The Deployment object consists of key attributes including `name`, `url`, `status`, and `metadata` that provide complete information about the deployed service.
{% endhint %}

   ```python
   from zenml.client import Client

   client = Client()
   
   # Deploy a pipeline
   deployment = client.deploy_pipeline(
       pipeline_name_or_id="weather_pipeline",
       deployment_name="weather_service",
       stack_name="k8s_deployment"
   )
   
   # Check deployment status
   if deployment.is_running:
       print(f"Pipeline service is running at {deployment.url}")
       
       # Invoke the deployed pipeline
       response = deployment.invoke(parameters={"city": "London", "temperature": 20})
       print(f"Pipeline response: {response}")
   else:
       print(f"Deployment status: {deployment.status}")
   ```

#### How to interact with deployments after creation?

When a Deployer is part of the active ZenML Stack, you can interact with it from the CLI to list, describe, invoke, and manage pipeline deployments:

```
$ zenml deployment list
┏━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃         NAME         │ PIPELINE                             │ URL                            │ STATUS                   ┃
┠──────────────────────┼──────────────────────────────────────┼────────────────────────────────┼──────────────────────────┨
┃  weather_service     │ weather_pipeline                     │ http://localhost:8001          │ ⚙ RUNNING               ┃
┠──────────────────────┼──────────────────────────────────────┼────────────────────────────────┼──────────────────────────┨
┃  ml_inference_api    │ inference_pipeline                   │ http://k8s-cluster/ml-api      │ ⚙ RUNNING               ┃
┗━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

$ zenml deployment describe weather_service
🚀 Deployment: weather_service is: RUNNING ⚙

Pipeline: weather_pipeline
Snapshot: 0866c821-d73f-456d-a98d-9aa82f41282e
Stack: k8s_deployment

📡 Connection Information:

Endpoint URL: http://localhost:8001
Swagger URL: http://localhost:8001/docs
CLI Command Example:
  zenml deployment invoke weather_service --city="London"

cURL Example:
  curl -X POST http://localhost:8001/invoke \
    -H "Content-Type: application/json" \
    -d '{"parameters": {"city": "London"}}'

$ zenml deployment invoke weather_service --city="Paris" --temperature=25
{
  "success": true,
  "outputs": {
    "weather_analysis": "The weather in Paris is 25 degrees Celsius"
  },
  "execution_time": 2.1,
  "metadata": {
    "deployment_name": "weather_service",
    "pipeline_name": "weather_pipeline"
  }
}

$ zenml deployment delete weather_service
```

In Python, you can also interact with deployments programmatically:

```python
from zenml.client import Client

client = Client()

# Get deployment information
deployment = client.get_deployment("weather_service")
print(f"Deployment URL: {deployment.url}")
print(f"Status: {deployment.status}")

# Invoke the deployment
response = deployment.invoke(parameters={"city": "Tokyo", "temperature": 18})
print(f"Pipeline output: {response['outputs']}")

# List all deployments
deployments = client.list_deployments()
for deployment in deployments:
    print(f"{deployment.name}: {deployment.status}")
```

#### Pipeline Requirements for Deployment

Not all pipelines are suitable for deployment as HTTP services. To be deployable, pipelines should follow these guidelines:

**Parameter Requirements:**
- Pipelines should accept explicit parameters with default values
- Parameters must be JSON-serializable types (int, float, str, bool, list, dict, Pydantic models)
- Parameter names should match step input names

**Output Requirements:**
- Pipelines should return meaningful values for HTTP responses
- Return values must be JSON-serializable
- Use type annotations to specify output artifact names

**Example Deployable Pipeline:**
```python
from typing import Annotated
from zenml import pipeline, step

@step
def process_weather(city: str, temperature: float) -> Annotated[str, "weather_analysis"]:
    return f"The weather in {city} is {temperature} degrees Celsius."

@pipeline
def weather_pipeline(city: str = "Paris", temperature: float = 20.0) -> str:
    """A deployable pipeline that processes weather data."""
    analysis = process_weather(city=city, temperature=temperature)
    return analysis

# Deploy the pipeline
deployment = weather_pipeline.deploy(deployment_name="weather_service")
```

The ZenML integrations that provide Deployer stack components also include standard pipeline steps and utilities for continuous deployment workflows. These components handle the aspects of deploying pipelines as services and managing their lifecycle through the deployment platform's APIs.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>