---
icon: microchip-ai
description: Ensuring your pipelines or steps run on GPU-backed hardware.
---

# Specify cloud resources

There are several reasons why you may want to scale your machine learning pipelines to the cloud, such as utilizing more powerful hardware or distributing tasks across multiple nodes. In order to achieve this with ZenML you'll need to run your steps on GPU-backed hardware using `ResourceSettings` to allocate greater resources on an orchestrator node and/or make some adjustments to the container environment.

## Specify resource requirements for steps

Some steps of your machine learning pipeline might be more resource-intensive and require special hardware to execute. In such cases, you can specify the required resources for steps as follows:

```python
from zenml.config import ResourceSettings
from zenml import step

@step(settings={"resources": ResourceSettings(cpu_count=8, gpu_count=2, memory="8GB")})
def training_step(...) -> ...:
    # train a model
```

If the underlying [orchestrator](../../component-guide/orchestrators/orchestrators.md) in your stack then supports specifying resources, this setting will attempt to secure these resources. Some orchestrators (like the [Skypilot orchestrator](../../component-guide/orchestrators/skypilot-vm.md)) do not support `ResourceSettings` directly, but rather use their `Orchestrator` specific settings to achieve the same effect:

```python
from zenml import step
from zenml.integrations.skypilot.flavors.skypilot_orchestrator_aws_vm_flavor import SkypilotAWSOrchestratorSettings

skypilot_settings = SkypilotAWSOrchestratorSettings(
    cpus="2",
    memory="16",
    accelerators="V100:2",
)


@step(settings={"orchestrator": skypilot_settings)
def training_step(...) -> ...:
    # train a model
```

Please refer to the source code and documentation of each orchestrator to find out which orchestrator supports specifying resources in what way.

{% hint style="info" %}
If you're using an orchestrator which does not support this feature or its underlying infrastructure does not cover your requirements, you can also take a look at [step operators](../../component-guide/step-operators/step-operators.md) which allow you to execute individual steps of your pipeline in environments independent of your orchestrator.
{% endhint %}

### Ensure your container is CUDA-enabled

To run steps or pipelines on GPUs, it's crucial to have the necessary CUDA tools installed in the environment. This section will guide you on how to configure your environment to utilize GPU capabilities effectively.

{% hint style="warning" %}
Note that these configuration changes are **required** for the GPU hardware to be properly utilized. If you don't update the settings, your steps might run, but they will not see any boost in performance from the custom hardware.
{% endhint %}

All steps running on GPU-backed hardware will be executed within a containerized environment, whether you're using the local Docker orchestrator or a cloud instance of Kubeflow. Therefore, you need to make two amendments to your Docker settings for the relevant steps:

#### 1. **Specify a CUDA-enabled parent image in your `DockerSettings`**

For complete details, refer to the [containerization page](../customize-docker-builds/README.md) that explains how to do this. As an example, if you want to use the latest CUDA-enabled official PyTorch image for your entire pipeline run, you can include the following code:

```python
from zenml import pipeline
from zenml.config import DockerSettings

docker_settings = DockerSettings(parent_image="pytorch/pytorch:1.12.1-cuda11.3-cudnn8-runtime")

@pipeline(settings={"docker": docker_settings})
def my_pipeline(...):
    ...
```

For TensorFlow, you might use the `tensorflow/tensorflow:latest-gpu` image, as detailed in the [official TensorFlow documentation](https://www.tensorflow.org/install/docker#gpu\_support) or their [DockerHub overview](https://hub.docker.com/r/tensorflow/tensorflow).

#### 2. **Add ZenML as an explicit pip requirement**

ZenML requires that ZenML itself be installed for the containers running your pipelines and steps. Therefore, you need to explicitly state that ZenML should be installed. There are several ways to specify this, but as an example, you can update the code from above as follows:

```python
from zenml.config import DockerSettings
from zenml import pipeline

docker_settings = DockerSettings(
    parent_image="pytorch/pytorch:1.12.1-cuda11.3-cudnn8-runtime",
    requirements=["zenml==0.39.1", "torchvision"]
)


@pipeline(settings={"docker": docker_settings})
def my_pipeline(...):
    ...
```

Adding these two extra settings options will ensure that CUDA is enabled for the specific steps that require GPU acceleration. Be cautious when choosing the image to avoid confusion when switching between local and remote environments. For example, you might have one version of PyTorch installed locally with a particular CUDA version, but when you switch to your remote stack or environment, you might be forced to use a different CUDA version.

The core cloud operators offer prebuilt Docker images that fit with their hardware. You can find more information on them here:

* [AWS](https://github.com/aws/deep-learning-containers/blob/master/available\_images.md)
* [GCP](https://cloud.google.com/deep-learning-vm/docs/images)
* [Azure](https://learn.microsoft.com/en-us/azure/machine-learning/concept-prebuilt-docker-images-inference)

Not all of these images are available on DockerHub, so ensure that the
orchestrator environment your pipeline runs in has sufficient permissions to
pull images from registries if you are using one of those.

### Reset the CUDA cache in between steps

Your use case will determine whether this is necessary or makes sense to do, but
we have seen that resetting the CUDA cache in between steps can help avoid issues
with the GPU cache. This is particularly necessary if your training jobs are
pushing the boundaries of the GPU cache. Doing so is simple; just use a helper
function to reset the cache at the beginning of any GPU-enabled steps. For
example, something as simple as this might suffice:

```python
import gc
import torch

def cleanup_memory() -> None:
    while gc.collect():
        torch.cuda.empty_cache()
```

You can then call this function at the beginning of your GPU-enabled steps:

```python
from zenml import step

@step
def training_step(...):
    cleanup_memory()
    # train a model
```

Note that resetting the memory cache will potentially affect others using the
same GPU, so use this judiciously.

## Train across multiple GPUs

ZenML supports training your models with multiple GPUs on a single node. This is
useful if you have a large dataset and want to train your model in parallel. The
most important thing that you'll have to handle is preventing multiple ZenML
instances from being spawned as you split the work among multiple GPUs.

In practice this will probably involve:

- creating a script / Python function that contains the logic of training your
  model (with the specification that this should run in parallel across multiple
  GPUs)
- calling that script / external function from within the step, possibly with
  some wrapper or helper code to dynamically configure or update the external
  script function

We're aware that this is not the most elegant solution and we're at work to
implement a better option with some inbuilt support for this task. If this is
something you're struggling with and need support getting the step code working,
please do [connect with us on Slack](https://zenml.io/slack) and we'll do our best
to help you out.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
