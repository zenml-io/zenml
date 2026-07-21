---
description: Deploying your LLM locally with vLLM.
---

# vLLM

[vLLM](https://docs.vllm.ai/en/latest/) is a fast and easy-to-use library for LLM inference and serving.

## When to use it?

You should use vLLM Model Deployer:

* Deploying Large Language models with state-of-the-art serving throughput creating an OpenAI-compatible API server
* Continuous batching of incoming requests
* Quantization: GPTQ, AWQ, INT4, INT8, and FP8
* Features such as PagedAttention, Speculative decoding, Chunked pre-fill

## How do you deploy it?

The vLLM Model Deployer flavor is provided by the vLLM ZenML integration, so you need to install it on your local machine to be able to deploy your models. You can do this by running the following command:

```bash
zenml integration install vllm -y
```

To register the vLLM model deployer with ZenML you need to run the following command:

```bash
zenml model-deployer register vllm_deployer --flavor=vllm
```

The ZenML integration will provision a local vLLM deployment server as a daemon process that will continue to run in the background to serve the latest vLLM model.

## How do you use it?

If you'd like to see this in action, check out this example of a [deployment pipeline](https://github.com/zenml-io/zenml-projects/blob/79f67ea52c3908b9b33c9a41eef18cb7d72362e8/llm-vllm-deployer/pipelines/deploy_pipeline.py#L25).

### Deploy an LLM

The [vllm_model_deployer_step](https://github.com/zenml-io/zenml-projects/blob/79f67ea52c3908b9b33c9a41eef18cb7d72362e8/llm-vllm-deployer/steps/vllm_deployer.py#L32) exposes a `VLLMDeploymentService` that you can use in your pipeline. Here is an example snippet:

```python

from zenml import pipeline
from typing import Annotated
from steps.vllm_deployer import vllm_model_deployer_step
from zenml.integrations.vllm.services.vllm_deployment import VLLMDeploymentService


@pipeline()
def deploy_vllm_pipeline(
    model: str,
    timeout: int = 1200,
) -> Annotated[VLLMDeploymentService, "GPT2"]:
    service = vllm_model_deployer_step(
        model=model,
        timeout=timeout,
    )
    return service
```

Here is an [example](https://github.com/zenml-io/zenml-projects/tree/79f67ea52c3908b9b33c9a41eef18cb7d72362e8/llm-vllm-deployer) of running a GPT-2 model using vLLM.

#### Configuration

Within the `VLLMDeploymentService` you can configure:

* `model`: Name or path of the Hugging Face model to use.
* `tokenizer`: Name or path of the Hugging Face tokenizer to use. If unspecified, model name or path will be used.
* `served_model_name`: The model name(s) used in the API. If not specified, the model name will be the same as the `model` argument.
* `trust_remote_code`: Trust remote code from Hugging Face.
* `tokenizer_mode`: The tokenizer mode. Allowed choices: ['auto', 'slow', 'mistral']
* `dtype`: Data type for model weights and activations. Allowed choices: ['auto', 'half', 'float16', 'bfloat16', 'float', 'float32']
* `revision`: The specific model version to use. It can be a branch name, a tag name, or a commit id. If unspecified, will use the default version.

## Deploying on Kubernetes

The `vllm-kubernetes` flavor deploys the vLLM OpenAI-compatible server as a long-lived Deployment and Service on a Kubernetes cluster, instead of running it as a local daemon process. It builds on the same [model deployer abstraction](README.md) as [Seldon Core](seldon.md), with the Kubernetes cluster reached through a `kubectl` context, an in-cluster configuration, or a [Service Connector](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/).

Only `deploy` and `delete` are supported for this flavor. Stopping and starting a deployed server raise `NotImplementedError`, delete it and deploy again instead.

### Installation

The Kubernetes flavor talks to the cluster through the `kubernetes` package and to the deployed server through the `openai` client. It does not need the `vllm` package itself. If you only need the Kubernetes flavor, you can skip the `vllm` install:

```bash
pip install kubernetes openai
```

`zenml integration install vllm -y` also works and additionally installs `vllm`, which is only needed for the local flavor.

### Registering the model deployer

```bash
zenml model-deployer register <MODEL_DEPLOYER_NAME> --flavor=vllm-kubernetes \
  --kubernetes_namespace=<KUBERNETES-NAMESPACE> \
  --hf_token=<HF_TOKEN>
```

You can configure:

* `kubernetes_context`: name of a `kubectl` context to deploy to. Ignored if the component is linked to a Kubernetes service connector.
* `kubernetes_namespace`: namespace vLLM deployments are provisioned into, defaults to `zenml-vllm`. Can be overridden per deployment.
* `incluster`: if `True`, connects using the configuration of the cluster the client itself runs in. Requires the client to run inside a Kubernetes pod, and ignores `kubernetes_context` when set.
* `default_image`: image used when a deployment doesn't specify its own, defaults to `vllm/vllm-openai:v0.25.1`.
* `default_service_type`: Kubernetes Service type used when a deployment doesn't specify its own, defaults to `LoadBalancer`.
* `hf_token`: Hugging Face access token used to download gated models, used as a fallback for deployments that configure neither their own token nor an existing secret.

### Using a service connector

As with Seldon Core, the recommended way to authenticate to the target cluster is [a Service Connector](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/) instead of `kubernetes_context`. Pick the connector for your cloud provider (AWS, GCP, Azure) or the generic [Kubernetes Service Connector](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/kubernetes-service-connector), then connect it to the model deployer:

```sh
zenml service-connector register <CONNECTOR_NAME> --type kubernetes --auto-configure

zenml model-deployer register <MODEL_DEPLOYER_NAME> --flavor=vllm-kubernetes
zenml model-deployer connect <MODEL_DEPLOYER_NAME> --connector <CONNECTOR_NAME>
```

We can now use the model deployer in our stack:

```bash
zenml stack update <CUSTOM_STACK_NAME> --model-deployer=<MODEL_DEPLOYER_NAME>
```

### Deploy an LLM

The deploy entry point is the same `deploy_model` method used by every model deployer. Here is an example step that deploys a gated Hugging Face model with a GPU:

```python
from typing import Annotated
from zenml import pipeline, step
from zenml.integrations.vllm.model_deployers import KubernetesVLLMModelDeployer
from zenml.integrations.vllm.services import (
    VLLMKubernetesDeploymentService,
    VLLMKubernetesServiceConfig,
)


@step
def deploy_vllm_kubernetes(
    model: str,
    timeout: int = 1200,
) -> Annotated[VLLMKubernetesDeploymentService, "vllm_deployment"]:
    model_deployer = KubernetesVLLMModelDeployer.get_active_model_deployer()

    service_config = VLLMKubernetesServiceConfig(
        model=model,
        resources={"limits": {"nvidia.com/gpu": "1"}},
        hf_token="<HF_TOKEN>",
    )

    service = model_deployer.deploy_model(
        config=service_config,
        service_type=VLLMKubernetesDeploymentService.SERVICE_TYPE,
        timeout=timeout,
    )
    return service


@pipeline
def deploy_vllm_kubernetes_pipeline(model: str, timeout: int = 1200):
    deploy_vllm_kubernetes(model=model, timeout=timeout)
```

`VLLMKubernetesServiceConfig` accepts the same engine arguments as the local `VLLMDeploymentService` (`model`, `tokenizer`, `served_model_name`, `trust_remote_code`, `tokenizer_mode`, `dtype`, `revision`), plus:

* `namespace`: Kubernetes namespace to deploy into. Falls back to the model deployer's `kubernetes_namespace` when unset.
* `image`: container image running the vLLM OpenAI server. Falls back to the model deployer's `default_image` when unset.
* `port`: port the vLLM OpenAI server listens on, defaults to `8000`.
* `service_type`: Kubernetes Service type used to expose the server. Falls back to the model deployer's `default_service_type` when unset.
* `replicas`: number of pod replicas for the Deployment, defaults to `1`.
* `resources`: native Kubernetes resource requests and limits for the container, e.g. `{"limits": {"nvidia.com/gpu": "1"}}`. A GPU limit is automatically mirrored into requests, since Kubernetes requires the two to match for extended resources.
* `pod_settings`: a `KubernetesPodSettings` object for node selectors, tolerations, affinity, and other pod configuration not modeled as a dedicated field.
* `hf_token`: Hugging Face access token injected into the container through a managed secret.
* `existing_hf_secret`: name of an existing Kubernetes secret to use instead of `hf_token`. Must contain the token under a `token` key.
* `env`: additional environment variables set on the container.
* `extra_serve_args`: additional CLI args appended to the vLLM OpenAI server args, for engine options not modeled as dedicated fields.
* `shm_size`: size limit of the `/dev/shm` volume mounted into the container, defaults to `2Gi`.

### Reaching the deployed server

A deployment that doesn't set its own `service_type` is exposed through the model deployer's `default_service_type`, which is `LoadBalancer` unless the deployer was registered with a different one, for example `--default_service_type=ClusterIP`.

With a `LoadBalancer` Service, point an OpenAI client at the external address assigned to the Service. With a `ClusterIP` Service, which only has an address inside the cluster, forward the Service port instead to reach it from your local machine:

```bash
kubectl port-forward -n <KUBERNETES-NAMESPACE> svc/<SERVICE_NAME> 8000:8000
```

and then point an OpenAI client at `http://localhost:8000/v1`.

### Custom images

`image` (per deployment) and `default_image` (on the model deployer) both accept any vLLM OpenAI-compatible image, and override the pinned default `vllm/vllm-openai:v0.25.1`. For clusters without a GPU, use a CPU-capable image such as `vllm/vllm-openai-cpu`.

### Teardown

```bash
zenml model-deployer models delete <SERVICE_UUID>
```

This deletes the Deployment, Service, and the managed secret if one was created for `hf_token`. The namespace itself is never deleted.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
