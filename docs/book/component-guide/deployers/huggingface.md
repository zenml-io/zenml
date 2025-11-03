---
description: Deploying your pipelines to Hugging Face Spaces.
---

# Hugging Face Deployer

[Hugging Face Spaces](https://huggingface.co/spaces) is a platform for hosting and sharing machine learning applications. The Hugging Face deployer is a [deployer](./) flavor included in the ZenML Hugging Face integration that deploys your pipelines to Hugging Face Spaces as Docker-based applications.

{% hint style="warning" %}
This component is only meant to be used within the context of a [remote ZenML installation](https://docs.zenml.io/getting-started/deploying-zenml). Usage with a local ZenML setup may lead to unexpected behavior!
{% endhint %}

## When to use it

You should use the Hugging Face deployer if:

* you're already using Hugging Face for model hosting or datasets.
* you want to share your ML pipelines as publicly accessible or private Spaces.
* you're looking for a simple, managed platform for deploying Docker-based applications.
* you want to leverage Hugging Face's infrastructure for hosting your pipeline deployments.
* you need an easy way to showcase ML workflows to the community.

## How to deploy it

{% hint style="info" %}
The Hugging Face deployer requires a remote ZenML installation. You must ensure that you are connected to the remote ZenML server before using this stack component.
{% endhint %}

In order to use a Hugging Face deployer, you need to first deploy [ZenML to the cloud](https://docs.zenml.io/getting-started/deploying-zenml/).

The only other requirement is having a Hugging Face account and generating an access token with write permissions.

## How to use it

To use the Hugging Face deployer, you need:

* The ZenML `huggingface` integration installed. If you haven't done so, run

  ```shell
  zenml integration install huggingface
  ```
* [Docker](https://www.docker.com) installed and running.
* A [remote artifact store](https://docs.zenml.io/stacks/artifact-stores/) as part of your stack.
* A [remote container registry](https://docs.zenml.io/stacks/container-registries/) as part of your stack.
* A [Hugging Face access token with write permissions](https://huggingface.co/settings/tokens)

### Hugging Face credentials

You need a Hugging Face access token with write permissions to deploy pipelines. You can create one at [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).

You have two different options to provide credentials to the Hugging Face deployer:

* Pass the token directly when registering the deployer using the `--token` parameter
* (recommended) Store the token in a ZenML secret and reference it using the `--secret_name` parameter

### Registering the deployer

The deployer can be registered as follows:

```shell
# Option 1: Direct token (not recommended for production)
zenml deployer register <DEPLOYER_NAME> \
    --flavor=huggingface \
    --token=<YOUR_HF_TOKEN>

# Option 2: Using a secret (recommended)
zenml secret create hf_token --token=<YOUR_HF_TOKEN>
zenml deployer register <DEPLOYER_NAME> \
    --flavor=huggingface \
    --secret_name=hf_token
```

### Configuring the stack

With the deployer registered, it can be used in the active stack:

```shell
# Register and activate a stack with the new deployer
zenml stack register <STACK_NAME> -D <DEPLOYER_NAME> ... --set
```

{% hint style="info" %}
ZenML will build a Docker image called `<CONTAINER_REGISTRY_URI>/zenml:<PIPELINE_NAME>` which will be referenced in a Dockerfile deployed to your Hugging Face Space. Check out [this page](https://docs.zenml.io/how-to/customize-docker-builds/) if you want to learn more about how ZenML builds these images and how you can customize them.
{% endhint %}

You can now [deploy any ZenML pipeline](https://docs.zenml.io/concepts/deployment) using the Hugging Face deployer:

```shell
zenml pipeline deploy --name my_deployment my_module.my_pipeline
```

### Additional configuration

For additional configuration of the Hugging Face deployer, you can pass the following `HuggingFaceDeployerSettings` attributes defined in the `zenml.integrations.huggingface.flavors.huggingface_deployer_flavor` module when configuring the deployer or defining or deploying your pipeline:

* Basic settings common to all Deployers:

  * `auth_key`: A user-defined authentication key to use to authenticate with deployment API calls.
  * `generate_auth_key`: Whether to generate and use a random authentication key instead of the user-defined one.
  * `lcm_timeout`: The maximum time in seconds to wait for the deployment lifecycle management to complete.

* Hugging Face Spaces-specific settings:

  * `space_hardware` (default: `None`): Hardware tier for the Space (e.g., `'cpu-basic'`, `'cpu-upgrade'`, `'t4-small'`, `'t4-medium'`, `'a10g-small'`, `'a10g-large'`). If not specified, uses free CPU tier.
  * `space_storage` (default: `None`): Persistent storage tier for the Space (e.g., `'small'`, `'medium'`, `'large'`). If not specified, no persistent storage is allocated.
  * `private` (default: `False`): Whether to create the Space as private. Public Spaces are visible to everyone.
  * `app_port` (default: `7860`): Port number where your deployment server listens. Hugging Face Spaces will route traffic to this port.

Check out [this docs page](https://docs.zenml.io/concepts/steps_and_pipelines/configuration) for more information on how to specify settings.

For example, if you wanted to deploy on GPU hardware with persistent storage, you would configure settings as follows:

```python
from zenml.integrations.huggingface.deployers import HuggingFaceDeployerSettings

huggingface_settings = HuggingFaceDeployerSettings(
    space_hardware="t4-small",
    space_storage="small",
    private=True,
)

@pipeline(
    settings={
        "deployer": huggingface_settings
    }
)
def my_pipeline(...):
    ...
```

### Managing deployments

Once deployed, you can manage your deployments using the ZenML CLI:

```shell
# List all deployments
zenml deployment list

# Get deployment status
zenml deployment describe <DEPLOYMENT_NAME>

# Get deployment logs
zenml deployment logs <DEPLOYMENT_NAME>

# Delete a deployment
zenml deployment delete <DEPLOYMENT_NAME>
```

The deployed pipeline will be available as a Hugging Face Space at:
```
https://huggingface.co/spaces/<YOUR_USERNAME>/<SPACE_PREFIX>-<DEPLOYMENT_NAME>
```

By default, the space prefix is `zenml` but this can be configured using the `space_prefix` parameter when registering the deployer.

## Deployment Modes

The Hugging Face deployer supports two deployment modes depending on your stack configuration:

### Mode 1: Image Reference (Stack with Container Registry)

When your ZenML stack includes a container registry, the deployer references a pre-built Docker image:

**How it works:**
- ZenML builds and pushes an image to your container registry
- The Dockerfile in Hugging Face Spaces references this image with `FROM <your-image>`
- The deployment server starts automatically with the correct entrypoint

**Requirements:**
- Container registry must be part of your stack
- ⚠️ **The Docker image must be publicly accessible** - Hugging Face Spaces cannot authenticate with private registries

**Use when:**
- You have a public container registry or public repository
- You want to pre-build images in your CI/CD pipeline
- You're using services like Docker Hub with public repositories

### Mode 2: Full Build (Stack without Container Registry)

When your stack does NOT have a container registry, the deployer builds the complete image from scratch in Hugging Face Spaces:

**How it works:**
- Deployer uploads your source code to the Space
- Generates a complete Dockerfile that installs all dependencies
- Hugging Face Spaces builds the entire image from your code
- ✅ **No private registry authentication needed!**

**Requirements:**
- No container registry in your stack
- Source code and dependencies uploadable to Hugging Face

**Use when:**
- You don't want to manage a container registry
- You want to avoid private registry authentication issues
- Your code and dependencies aren't too large for uploading
- You're okay with longer build times in Hugging Face Spaces

### Private Registry Workaround

If you're currently using a private registry and want to deploy to Hugging Face, you have two options:

1. **Remove the container registry from your stack** to automatically use Full Build Mode:
```shell
# Create a new stack without container registry
zenml stack copy my-stack hf-stack
zenml stack update hf-stack --container-registry=null
zenml stack set hf-stack
```

2. **Use a public container registry** for Hugging Face deployments:
```shell
zenml container-registry register public_registry \
    --flavor=default \
    --uri=docker.io/<your-public-username>
```

## Additional Resources

* [Hugging Face Spaces Documentation](https://huggingface.co/docs/hub/spaces)
* [Docker Spaces Guide](https://huggingface.co/docs/hub/spaces-sdks-docker)
* [Hugging Face Hardware Options](https://huggingface.co/docs/hub/spaces-gpus)
* [ZenML Deployment Concepts](https://docs.zenml.io/concepts/deployment)
