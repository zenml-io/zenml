---
description: Deploying your LLM locally with vLLM.
---

# vLLM

## When to use it?

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

#### Configuration

Within the `VLLMDeploymentService` you can configure:

* `model`: Name or path of the huggingface model to use.
* `tokenizer`: Name or path of the huggingface tokenizer to use. If unspecified, model name or path will be used.
* `served_model_name`: The model name(s) used in the API. If not specified, the model name will be the same as the `model` argument.
* `trust_remote_code`: Trust remote code from huggingface.
* `tokenizer_mode`: The tokenizer mode. Allowed choices: ['auto', 'slow', 'mistral']
* `dtype`: Data type for model weights and activations. Allowed choices: ['auto', 'half', 'float16', 'bfloat16', 'float', 'float32']
* `revision`: The specific model version to use. It can be a branch name, a tag name, or a commit id. If unspecified, will use the default version.
