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

You don't need to directly interact with the ZenML deployer stack component in your code. As long as the deployer that you want to use is part of your active [ZenML stack](../../user-guide/production-guide/understand-stacks.md), you can simply deploy a pipeline or snapshot using the ZenML CLI or the ZenML SDK. The resulting deployment can be managed using the ZenML CLI or the ZenML SDK.

Example:

* set up a stack with a deployer:

```bash
zenml deployer register docker --flavor=local
zenml stack register docker_deployment -a default -o default -D docker --set
```

* deploy a pipeline with the ZenML SDK:

```python
from zenml import pipeline

@step
def my_step(name: str) -> str:
    return f"Hello, {name}!"

@pipeline
def my_pipeline(name: str = "John") -> str:
    return my_step(name=name)

if __name__ == "__main__":
    # Deploy the pipeline `my_pipeline` as a deployment named `my_deployment`
    deployment = my_pipeline.deploy(deployment_name="my_deployment")
    print(f"Deployment URL: {deployment.url}")
```

* deploy the same pipeline with the CLI:

```bash
zenml pipeline deploy --name my_deployment my_module.my_pipeline
```

* send a request to the deployment with the ZenML CLI:

```bash
zenml deployment invoke my_deployment --name="Alice"
```

* or with curl:

```bash
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"name": "Alice"}}'
```

* alternatively, set up a snapshot and deploy it instead of a pipeline:

```bash
zenml pipeline snapshot create --name my_snapshot my_module.my_pipeline
zenml pipeline snapshot deploy my_snapshot --deployment my_deployment
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
- It's recommended to use type annotations to specify output artifact names

Example Deployable Pipeline:

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
```

For more information, see the [Deployable Pipeline Requirements](../../how-to/deployment/deployment.md#deployable-pipeline-requirements) section of the tutorial.

#### Deployment Lifecycle Management

The Deployment object represents a pipeline that has been deployed to a serving environment. The Deployment object is saved in the ZenML database and contains information about the deployment configuration, status, and connection details. Deployments are standalone entities that can be managed independently of the active stack through the Deployer stack components that were originally used to provision them.

Some example of how to manage deployments:

* listing deployments with the CLI:

```bash
$ zenml deployment list
┏━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃         NAME         │ PIPELINE                             │ URL                            │ STATUS                   ┃
┠──────────────────────┼──────────────────────────────────────┼────────────────────────────────┼──────────────────────────┨
┃  weather_service     │ weather_pipeline                     │ http://localhost:8001          │ ⚙ RUNNING               ┃
┠──────────────────────┼──────────────────────────────────────┼────────────────────────────────┼──────────────────────────┨
┃  ml_inference_api    │ inference_pipeline                   │ http://k8s-cluster/ml-api      │ ⚙ RUNNING               ┃
┗━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

* listing deployments with the SDK:

```python
from zenml.client import Client

client = Client()
deployments = client.list_deployments()
for deployment in deployments:
    print(f"{deployment.name}: {deployment.status}")
```

* showing detailed information about a deployment with the CLI:

```bash
$ zenml deployment describe my_deployment --show-schema

🚀 Deployment: my_deployment is: RUNNING ⚙

Pipeline: my_pipeline
Snapshot: my_snapshot
Stack: docker-deployer

📡 Connection Information:

Endpoint URL: http://localhost:8002
Swagger URL: http://localhost:8002/docs
CLI Command Example:
  zenml deployment invoke my_deployment --name="John"

cURL Example:
  curl -X POST http://localhost:8002/invoke \
    -H "Content-Type: application/json" \
    -d '{
      "parameters": {
        "name": "John"
      }
    }'

📋 Deployment JSON Schemas:

Input Schema:
{
  "additionalProperties": false,
  "properties": {
    "name": {
      "default": "John",
      "title": "Name",
      "type": "string"
    }
  },
  "title": "PipelineInput",
  "type": "object"
}

Output Schema:
{
  "properties": {
    "output": {
      "title": "Output",
      "type": "string"
    }
  },
  "required": [
    "output"
  ],
  "title": "PipelineOutput",
  "type": "object"
}

⚙️  Management Commands
╭────────────────────────────────────────────┬─────────────────────────────────────────────────────╮
│ zenml deployment logs my_deployment -f     │ Follow deployment logs in real-time                 │
│ zenml deployment describe my_deployment    │ Show detailed deployment information                │
│ zenml deployment deprovision my_deployment │ Deprovision this deployment and keep a record of it │
│ zenml deployment delete my_deployment      │ Deprovision and delete this deployment              │
╰────────────────────────────────────────────┴─────────────────────────────────────────────────────╯
```

* showing detailed information about a deployment with the SDK:

```python
from zenml.client import Client
deployment = client.get_deployment("my_deployment")
print(deployment)
```

* deprovision and delete a deployment with the CLI:

```bash
$ zenml deployment delete my_deployment
```

* deprovisioning and deleting a deployment with the SDK:
```python
from zenml.client import Client
client = Client()
client.delete_deployment("my_deployment")
```

* sending a request to a deployment with the CLI:

```bash
$ zenml deployment invoke my_deployment --name="John"

Invoked deployment 'my_deployment' with response:
{
  "success": true,
  "outputs": {
    "output": "Hello, John!"
  },
  "execution_time": 3.2781872749328613,
  "metadata": {
    "deployment_id": "95d60dcf-7c37-4e62-a923-a341601903e5",
    "deployment_name": "my_deployment",
    "snapshot_id": "f3122ed4-aa13-4113-9f60-a80545f56244",
    "snapshot_name": "my_snapshot",
    "pipeline_name": "my_pipeline",
    "run_id": "ea448522-d5bf-411e-971e-d4550fdbe713",
    "run_name": "my_pipeline-2025_09_30-12_52_01_012491",
    "parameters_used": {}
  },
  "error": null
}
```

* sending a request to a deployment with the SDK:

```python
from zenml.deployers.utils import invoke_deployment

response = invoke_deployment(
    deployment_name_or_id="my_deployment",
    name="John",
)
print(response)
```

#### Specifying deployment resources

If your steps require additional hardware resources, you can specify them on your steps as described [here](https://docs.zenml.io/user-guides/tutorial/distributed-training/).

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>