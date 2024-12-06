---
description: Deploying your LLM locally with vLLM.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


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
