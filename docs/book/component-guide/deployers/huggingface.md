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
  * `app_port` (default: `8000`): Port number where your deployment server listens. Defaults to 8000 (ZenML server default). Hugging Face Spaces will route traffic to this port.

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

## Important Requirements

### Secure Secrets and Environment Variables

{% hint style="success" %}
The Hugging Face deployer handles secrets and environment variables **securely** using Hugging Face's Space Secrets and Variables API. Credentials are **never** written to the Dockerfile.
{% endhint %}

**How it works:**
- Environment variables are set using `HfApi.add_space_variable()` - stored securely by Hugging Face
- Secrets are set using `HfApi.add_space_secret()` - encrypted and never exposed in the Space repository
- **Nothing is baked into the Dockerfile** - no risk of leaked credentials even in public Spaces

**What this means:**
- ✅ Safe to use with public Spaces (the default)
- ✅ Secrets remain encrypted and hidden from public view
- ✅ Environment variables are managed through HF's secure API
- ✅ No credentials exposed in Dockerfile or repository files

This is especially important since Hugging Face Spaces are **public by default** (`private: bool = False`). Without this secure approach, any secrets would be visible to anyone viewing your Space's repository.

### Container Registry Requirement

{% hint style="warning" %}
The Hugging Face deployer **requires** a container registry to be part of your ZenML stack. The Docker image must be pre-built and pushed to a **publicly accessible** container registry.
{% endhint %}

**Why public access is required:**
Hugging Face Spaces cannot authenticate with private Docker registries when building Docker Spaces. The platform pulls your Docker image during the build process, which means it needs public access.

**Recommended registries:**
- [Docker Hub](https://hub.docker.com/) public repositories
- [GitHub Container Registry (GHCR)](https://ghcr.io) with public images
- Any other public container registry

**Example setup with GitHub Container Registry:**
```shell
# Register a public container registry
zenml container-registry register ghcr_public \
    --flavor=default \
    --uri=ghcr.io/<your-github-username>

# Add it to your stack
zenml stack update <STACK_NAME> --container-registry=ghcr_public
```

### Configuring iframe Embedding (X-Frame-Options)

By default, ZenML's deployment server sends an `X-Frame-Options` header that prevents the deployment UI from being embedded in iframes. This causes issues with Hugging Face Spaces, which displays deployments in an iframe.

**To fix this**, you must configure your pipeline's `DeploymentSettings` to disable the `X-Frame-Options` header:

```python
from zenml import pipeline
from zenml.config import DeploymentSettings, SecureHeadersConfig

# Configure deployment settings
deployment_settings = DeploymentSettings(
    app_title="My ZenML Pipeline",
    app_description="ML pipeline deployed to Hugging Face Spaces",
    app_version="1.0.0",
    secure_headers=SecureHeadersConfig(
        xfo=False,  # Disable X-Frame-Options to allow iframe embedding
        server=True,
        hsts=False,
        content=True,
        referrer=True,
        cache=True,
        permissions=True,
    ),
    cors={
        "allow_origins": ["*"],
        "allow_methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["*"],
        "allow_credentials": False,
    },
)

@pipeline(
    name="my_hf_pipeline",
    settings={"deployment": deployment_settings}
)
def my_pipeline():
    # Your pipeline steps here
    pass
```

Without this configuration, the Hugging Face Spaces UI will show a blank page or errors when trying to display your deployment.

## Additional Resources

* [Hugging Face Spaces Documentation](https://huggingface.co/docs/hub/spaces)
* [Docker Spaces Guide](https://huggingface.co/docs/hub/spaces-sdks-docker)
* [Hugging Face Hardware Options](https://huggingface.co/docs/hub/spaces-gpus)
* [ZenML Deployment Concepts](https://docs.zenml.io/concepts/deployment)
