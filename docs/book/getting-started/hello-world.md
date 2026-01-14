---
description: >-
  Your first ML pipeline with ZenML - from local development to cloud deployment
  in minutes.
icon: hand-wave
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Hello World

This guide will help you build and deploy your first ZenML pipeline, starting locally and then transitioning to the cloud without changing your code. The same principles you'll learn here apply whether you're building classical ML models or AI agents.

{% stepper %}
{% step %}
#### Install ZenML

Start by installing ZenML in a fresh Python environment:

```bash
pip install 'zenml[server]'
zenml login
```

This gives you access to both the ZenML Python SDK and CLI tools. It also surfaces the
ZenML dashboard + connects it to your local client.
{% endstep %}

{% step %}
#### Write your first pipeline

Create a simple `run.py` file with a basic workflow:

<pre class="language-python"><code class="lang-python">from zenml import step, pipeline


@step
def basic_step() -> str:
    """A simple step that returns a greeting message."""
    return "Hello World!"


@pipeline
def basic_pipeline() -> str:
    """A simple pipeline with just one step."""
    greeting = basic_step()
    return greeting


if __name__ == "__main__":
<strong>    basic_pipeline()
</strong></code></pre>

Run this pipeline in batch mode locally:

```bash
python run.py
```
 
You will see ZenML automatically tracks the execution and stores artifacts. View these on the CLI or on the dashboard.

{% endstep %}

{% step %}
#### Create a Pipeline Snapshot (Optional but Recommended)

Before deploying, you can create a **snapshot** - an immutable, reproducible version of your pipeline including code, configuration, and container images:

```bash
# Create a snapshot of your pipeline
zenml pipeline snapshot create run.basic_pipeline --name my_snapshot
```

Snapshots are powerful because they:
- **Freeze your pipeline state** - Ensure the exact same pipeline always runs
- **Enable parameterization** - Run the same snapshot with different inputs
- **Support team collaboration** - Share ready-to-use pipeline configurations
- **Integrate with automation** - Trigger from dashboards, APIs, or CI/CD systems

[Learn more about Snapshots](../how-to/snapshots/snapshots.md)
{% endstep %}

{% step %}
#### Deploy your pipeline as a real-time service

ZenML can deploy your pipeline (or snapshot) as a persistent HTTP service for real-time inference:

```bash
# Deploy your pipeline directly
zenml pipeline deploy run.basic_pipeline --name my_deployment

# OR deploy a snapshot (if you created one above)
zenml pipeline snapshot deploy my_snapshot --deployment my_deployment
```

Your pipeline now runs as a production-ready service! This is perfect for serving predictions to web apps, powering AI agents, or handling real-time requests.

**Key insight**: When you deploy a pipeline directly with `zenml pipeline deploy`, ZenML automatically creates an implicit snapshot behind the scenes, ensuring reproducibility.

[Learn more about Pipeline Deployments](../how-to/deployment/deployment.md)
{% endstep %}

{% step %}
#### Set up a ZenML Server (For Remote Infrastructure)

To use remote infrastructure (cloud deployers, orchestrators, artifact stores), you need to deploy a ZenML server to manage your pipelines centrally. You can use [ZenML Pro](https://zenml.io/pro) (managed, 14-day free trial) or [deploy it yourself](../getting-started/deploying-zenml/README.md) (self-hosted, open-source).

Connect your local environment:

```bash
zenml login
zenml project set <PROJECT_NAME>
```

Once connected, you'll have a centralized dashboard to manage infrastructure, collaborate with team members, and schedule pipeline runs.
{% endstep %}

{% step %}
#### Create your first remote stack (Optional)

A "stack" in ZenML represents the infrastructure where your pipelines run. You can now scale from local development to cloud infrastructure without changing any code.

<figure><img src="../.gitbook/assets/stack-deployment-options.png" alt="ZenML Stack Deployment Options"><figcaption><p>Stack deployment options</p></figcaption></figure>

Remote stacks can include:
- **[Remote Deployers](https://docs.zenml.io/stacks/stack-components/deployers)** ([AWS App Runner](https://docs.zenml.io/stacks/stack-components/deployers/aws-app-runner), [GCP Cloud Run](https://docs.zenml.io/stacks/stack-components/deployers/gcp-cloud-run), [Azure Container Instances](https://docs.zenml.io/stacks/stack-components/container-registries/azure)) - for deploying your pipelines as scalable HTTP services on the cloud
- **[Remote Orchestrators](https://docs.zenml.io/stacks/stack-components/orchestrators)** ([Kubernetes](https://docs.zenml.io/stacks/stack-components/orchestrators/kubernetes), [GCP Vertex AI](https://docs.zenml.io/stacks/stack-components/orchestrators/vertex), [AWS SageMaker](https://docs.zenml.io/stacks/stack-components/orchestrators/sagemaker)) - for running batch pipelines at scale
- **[Remote Artifact Stores](https://docs.zenml.io/stacks/stack-components/artifact-stores)** ([S3](https://docs.zenml.io/stacks/stack-components/artifact-stores/s3), [GCS](https://docs.zenml.io/stacks/stack-components/artifact-stores/gcp), [Azure Blob](https://docs.zenml.io/stacks/stack-components/artifact-stores/azure)) - for storing and versioning pipeline artifacts

The fastest way to create a cloud stack is through the **Infrastructure-as-Code** option, which uses Terraform to deploy cloud resources and register them as a ZenML stack.

You'll need:

* [Terraform](https://developer.hashicorp.com/terraform/install) version 1.9+ installed locally
* Authentication configured for your preferred cloud provider (AWS, GCP, or Azure)
* Appropriate permissions to create resources in your cloud account

```bash
# Create a remote stack using the deployment wizard
zenml stack register <STACK_NAME> \
  --deployer <DEPLOYER_NAME> \
  --orchestrator <ORCHESTRATOR_NAME> \
  --artifact-store <ARTIFACT_STORE_NAME>
```

The wizard will guide you through each step.
{% endstep %}

{% step %}
#### Deploy and run on remote infrastructure

Once you have a remote stack, you can:

1. **Deploy your service to the cloud** - Your deployment runs on managed cloud infrastructure:
```bash
zenml stack set <REMOTE_STACK_NAME>
zenml pipeline deploy run.basic_pipeline --name my_production_deployment
```

2. **Run batch pipelines at scale** - Use the same code with a cloud orchestrator:
```bash
zenml stack set <REMOTE_STACK_NAME>
python run.py  # Automatically runs on cloud infrastructure
```

ZenML handles packaging code, building containers, orchestrating execution, and tracking artifacts automatically across all cloud providers.

<figure><img src="../.gitbook/assets/pipeline-run-on-the-dashboard.png" alt="Pipeline Run in ZenML Dashboard"><figcaption><p>Your pipeline in the ZenML Pro Dashboard</p></figcaption></figure>
{% endstep %}

{% step %}
#### What's next?

Congratulations! You've just experienced the core value proposition of ZenML:

* **Write Once, Run Anywhere**: The same code runs locally during development and in the cloud for production
* **Unified Framework**: Use the same MLOps principles for both classical ML models and AI agents
* **Separation of Concerns**: Infrastructure configuration and ML code are completely decoupled, enabling independent 
evolution of each
* **Full Tracking**: Every run, artifact, and model is automatically versioned and tracked - whether it's a scikit-learn model or a multi-agent system

To continue your ZenML journey, explore these key topics:

**For All AI Workloads:**
* **Pipeline Development**: Discover advanced features like [scheduling](../how-to/steps-pipelines/advanced_features.md#scheduling) and [caching](../how-to/steps-pipelines/advanced_features.md#caching)
* **Artifact Management**: Learn how ZenML [stores, versions, and tracks your data](../how-to/artifacts/artifacts.md) automatically
* **Organization**: Use [tags](../how-to/tags/tags.md) and [metadata](../how-to/metadata/metadata.md) to keep your AI projects structured

**For LLMs and AI Agents:**
* **LLMOps Guide**: Write your [first AI pipeline](your-first-ai-pipeline.md) for agent development patterns
* **Deploying Agents**: To see an example of a deployed document extraction agent, see the [deploying agents](https://github.com/zenml-io/zenml/tree/main/examples/deploying_agent) example
* **Agent Outer Loop**: See the [Agent Outer Loop](https://github.com/zenml-io/zenml/tree/main/examples/agent_outer_loop) example to learn about training classifiers and improving agents through feedback loops
* **Agent Evaluation**: Learn to [systematically evaluate](https://github.com/zenml-io/zenml/tree/main/examples/agent_comparison) and compare different agent architectures
* **Prompt Management**: Version and track prompts, tools, and agent configurations as [artifacts](../how-to/artifacts/artifacts.md)

**Infrastructure & Deployment:**
* **Containerization**: Understand how ZenML [handles containerization](../how-to/containerization/containerization.md) for reproducible execution
* **Stacks & Infrastructure**: Explore the concepts behind [stacks](../how-to/stack-components/stack_components.md) and [service connectors](../how-to/stack-components/service_connectors.md) for authentication
* **Secrets Management**: Learn how to [handle sensitive information](../how-to/secrets/secrets.md) securely
* **Snapshots**: Create [reusable snapshots](../how-to/snapshots/snapshots.md) for standardized workflows
{% endstep %}
{% endstepper %}
