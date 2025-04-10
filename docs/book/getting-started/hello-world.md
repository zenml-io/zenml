---
description: Your first ML pipeline with ZenML - from local development to cloud deployment in minutes.
icon: hand-wave
---

# Hello World

This guide will help you build and deploy your first ZenML pipeline. You'll start locally and then seamlessly transition to running the same pipeline in the cloud - all without changing your code.

{% stepper %}
{% step %}
### Install ZenML

Start by installing ZenML in a fresh Python environment:

```bash
pip install zenml
```

This single command gives you access to both the ZenML Python SDK for building pipelines and the ZenML CLI for managing your MLOps infrastructure.
{% endstep %}

{% step %}
### Write your first pipeline

Now, create a simple `run.py` file that defines a basic ML workflow using ZenML's Python decorators:

<pre class="language-python"><code class="lang-python">from zenml import step, pipeline


@step
def basic_step() -> str:
    """A simple step that returns a greeting message."""
    return "Hello World!"


@pipeline
def basic_pipeline():
    """A simple pipeline with just one step."""
    basic_step()


if __name__ == "__main__":
<strong>    basic_pipeline()
</strong></code></pre>

{% hint style="success" %}
You can run this pipeline locally right now with `python run.py`. ZenML will automatically track the execution and store artifacts, even in this local mode.
{% endhint %}
{% endstep %}

{% step %}
### Create your ZenML account

To unlock the full potential of ZenML, create a [ZenML Pro account](https://zenml.io/pro). It comes with a 14-day free trial with no payment information required.

ZenML Pro provides a powerful dashboard that helps you:
- Visualize your ML pipelines and their execution history
- Manage your infrastructure and cloud resources
- Track artifacts and model versions
- Collaborate with team members

<figure><img src="../.gitbook/assets/dcp_walkthrough (1).gif" alt="ZenML Pro Dashboard"><figcaption>The ZenML Pro Dashboard helps you manage all aspects of your ML workflows</figcaption></figure>

If this is your first time logging in to ZenML Pro, you'll need to set up a workspace and project. This process typically takes a few minutes. While waiting, we recommend reading through the [Core Concepts](core-concepts.md) to understand ZenML's architecture.

Once your workspace is ready, connect your local environment:

```bash
# Log in and select your workspace
zenml login

# Activate your project
zenml project set <PROJECT_NAME>
```
{% endstep %}

{% step %}
### Create your first remote stack

A "stack" in ZenML represents the infrastructure where your pipelines run. While you've been using a local stack so far, ZenML really shines when connecting to cloud resources.

<figure><img src="../.gitbook/assets/Screenshot 2025-04-09 at 14.56.35.png" alt="ZenML Stack Deployment Options"><figcaption>ZenML offers multiple ways to deploy your ML infrastructure to the cloud</figcaption></figure>

The fastest way to create a cloud stack is through the **Infrastructure-as-Code** option. This uses ZenML's Terraform modules to automatically:
1. Deploy the necessary cloud resources (storage, compute, etc.)
2. Configure them for optimal ML workloads
3. Register them back to your ZenML server as a ready-to-use stack

Requirements for this approach:
* [Terraform](https://www.terraform.io/downloads.html) version 1.9+ installed locally
* Authentication configured for your preferred cloud provider (AWS, GCP, or Azure)
* Appropriate permissions to create resources in your cloud account

The deployment wizard in the ZenML dashboard will guide you through the process step-by-step, automatically generating the necessary configuration based on your selections.
{% endstep %}

{% step %}
### Run your pipeline on the remote stack

Now for the magic moment - running your pipeline in the cloud without changing any code!

First, activate your newly created cloud stack:

```bash
zenml stack set <NAME_OF_YOUR_NEW_STACK>
```

Then, run the exact same Python script as before:

```bash
python run.py
```

ZenML automatically handles all the complexity behind the scenes:
- Packaging your code and dependencies
- Building container images if needed
- Orchestrating the execution on your cloud infrastructure
- Tracking artifacts and metadata

You can monitor the execution in real-time through the ZenML dashboard:

<figure><img src="../.gitbook/assets/Screenshot 2025-04-09 at 15.02.42.png" alt="Pipeline Run in ZenML Dashboard"><figcaption>Your pipeline execution is fully tracked and visualized in the ZenML dashboard</figcaption></figure>
{% endstep %}

{% step %}
### What's next?

Congratulations! You've just experienced the core value proposition of ZenML:

* **Write Once, Run Anywhere**: The same code runs locally during development and in the cloud for production
* **Infrastructure Abstraction**: Focus on your ML logic instead of cloud configuration
* **Full Tracking**: Every run, artifact, and model is automatically versioned and tracked

To continue your ZenML journey, explore these key topics:

* **Pipeline Development**: Discover advanced features like [scheduling](../how-to/pipeline-development/build-pipelines/schedule-a-pipeline.md), [caching](../how-to/steps-pipelines/advanced_features.md#caching), and [parameterization](../how-to/pipeline-development/use-configuration-files/runtime-configuration.md)
* **Artifact Management**: Learn how ZenML [stores, versions, and tracks your data](../how-to/artifacts/artifacts.md) automatically
* **Organization**: Use [tags and metadata](../how-to/tag-runs-and-artifacts.md) to keep your ML projects structured
* **Containerization**: Understand how ZenML [handles containerization](../how-to/containerization/containerize-your-pipeline.md) for reproducible execution
* **Stacks & Infrastructure**: Explore the [stack concept](../how-to/stack-components/stack_components.md) and [service connectors](../how-to/stack-components/service_connectors.md) for authentication
* **Secrets Management**: Learn how to [handle sensitive information](../how-to/infrastructure-deployment/auth-management/manage-secrets.md) securely
* **Templates**: Create [reusable pipeline templates](../how-to/trigger-pipelines/use-templates-python.md) for standardized workflows

{% endstep %}
{% endstepper %}
