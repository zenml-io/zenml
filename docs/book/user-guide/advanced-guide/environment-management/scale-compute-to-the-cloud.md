---
description: Ensuring your pipelines or steps run on GPU-backed hardware.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Scale compute to the cloud

There are several reasons why you may want to scale your machine learning pipelines to the cloud, such as utilizing more powerful hardware or distributing tasks across multiple nodes. In order to achieve this with ZenML you'll need to run your steps on GPU-backed hardware using `ResourceSettings` to allocate greater resources on an orchestrator node and/or make some adjustments to the container environment.

## Specify resource requirements for steps

Some steps of your machine learning pipeline might be more resource-intensive and require special hardware to execute. In such cases, you can specify the required resources for steps as follows:

```python
from zenml import ResourceSettings
from zenml import step

@step(settings={"resources": ResourceSettings(cpu_count=8, gpu_count=2, memory="8GB")})
def training_step(...) -> ...:
    # train a model
```

If the underlying [orchestrator](../../component-guide/orchestrators/orchestrators.md) in your stack then supports specifying resources, this setting will attempt to secure these resources. Please refer to the source code and documentation of each orchestrator to find out which orchestrator supports specifying resources.

{% hint style="info" %}
If you're using an orchestrator which does not support this feature or its underlying infrastructure doesn't cover your requirements, you can also take a look at [step operators](../../component-guide/step-operators/step-operators.md) which allow you to execute individual steps of your pipeline in environments independent of your orchestrator.
{% endhint %}

### Ensure your container is CUDA-enabled

To run steps or pipelines on GPUs, it's crucial to have the necessary CUDA tools installed in the environment. This section will guide you on how to configure your environment to utilize GPU capabilities effectively.

{% hint style="warning" %}
Note that these configuration changes are **required** for the GPU hardware to be properly utilized. If you don't update the settings, your steps might run, but they will not see any boost in performance from the custom hardware.
{% endhint %}

All steps running on GPU-backed hardware will be executed within a containerized environment, whether you're using the local Docker orchestrator or a cloud instance of Kubeflow. Therefore, you need to make two amendments to your Docker settings for the relevant steps:

#### 1. **Specify a CUDA-enabled parent image in your `DockerSettings`**

For complete details, refer to the [containerization page](containerize-your-pipeline.md) that explains how to do this. As an example, if you want to use the latest CUDA-enabled official PyTorch image for your entire pipeline run, you can include the following code:

```python
from zenml import pipeline

docker_settings = DockerSettings(parent_image="pytorch/pytorch:1.12.1-cuda11.3-cudnn8-runtime")

@pipeline(settings={"docker": docker_settings})
def my_pipeline(...):
    ...
```

For TensorFlow, you might use the `tensorflow/tensorflow:latest-gpu` image, as detailed in the [official TensorFlow documentation](https://www.tensorflow.org/install/docker#gpu\_support) or their [DockerHub overview](https://hub.docker.com/r/tensorflow/tensorflow).

#### 2. **Add ZenML as an explicit pip requirement**

ZenML requires that ZenML itself be installed for the containers running your pipelines and steps. Therefore, you need to explicitly state that ZenML should be installed. There are several ways to specify this, but as an example, you can update the code from above as follows:

```python
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

Not all of these images are available on DockerHub, so ensure that the orchestrator environment your pipeline runs in has sufficient permissions to pull images from registries if you are using one of those.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
