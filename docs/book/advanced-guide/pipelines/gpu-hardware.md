---
description: How to ensure your pipelines or steps run on GPU-backed hardware
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


ZenML allows for multiple ways to configure the hardware on which your steps
run, from [step operator stack
components](../../component-gallery/step-operators/step-operators.md) to [custom
per-step or per-pipeline
requirements](../../advanced-guide/pipelines/settings.md). For steps or
pipelines that are required to run on GPUs, it is essential to ensure that the
environment has the required CUDA tools installed. The following section describes what
you need to do to ensure that you will actually get the performance boost that
running your training on a GPU will give you.

The steps that will run on GPU-backed hardware will all be running from a
containerized environment, whether you're using our local Docker orchestrator or
on a cloud instance of Kubeflow. (Please see [the section on configuration of the
Docker environment](../../advanced-guide/pipelines/containerization.md) for
general context on this and what follows.) For this reason, you will need to
make two amendments to your Docker settings for the relevant steps as follows:

1. Specify a CUDA-enabled parent image in your `DockerSettings`

For full details, see the whole section where we explain how to do this [on the
containerization page](../../advanced-guide/pipelines/containerization.md). As
an example, if you wanted to use the latest CUDA-enabled official PyTorch image
for your entire pipeline run, you could include the following code:

```python
docker_settings = DockerSettings(parent_image="pytorch/pytorch:1.12.1-cuda11.3-cudnn8-runtime")

@pipeline(settings={"docker": docker_settings})
def my_pipeline(...):
    ...
```

If you were using Tensorflow, perhaps you might use the
`tensorflow/tensorflow:latest-gpu` image as detailed in [the official TensorFlow
documentation](https://www.tensorflow.org/install/docker#gpu_support) or in
[their DockerHub overview](https://hub.docker.com/r/tensorflow/tensorflow).

2. Add ZenML as an explicit pip requirement

ZenML requires that ZenML itself be installed for the containers running our
pipelines and steps, so you will also need to explicitly state that ZenML should
be installed. There are lots of ways to specify this, but as one example, you
could do the following (updating the code from above):

```python
docker_settings = DockerSettings(parent_image="pytorch/pytorch:1.12.1-cuda11.3-cudnn8-runtime", requirements=["zenml==0.20.5", "torchvision"])

@pipeline(settings={"docker": docker_settings})
def my_pipeline(...):
    ...
```

Adding these two extra settings options will be enough to ensure that
CUDA is enabled for the specific steps that require GPU acceleration. Note that these configuration changes
are **required** for the GPU hardware to be properly utilized. If you don't
update the settings, your steps might run but they will not see any boost in
performance from the custom hardware.

Note that you need to be quite careful with the image that you choose so that
switching between local and remote environments doesn't get muddled. For
example, you might have one version of PyTorch installed locally with a
particular CUDA version, but then when you switch to your remote stack or
environment you might be forced to use a different CUDA version.

The core cloud operators all offer prebuilt Docker images that fit with their
hardware. You can find more information on them here:

- [AWS](https://github.com/aws/deep-learning-containers/blob/master/available_images.md)
- [GCP](https://cloud.google.com/deep-learning-vm/docs/images)
- [Azure](https://learn.microsoft.com/en-us/azure/machine-learning/concept-prebuilt-docker-images-inference)

Not all of these images are available on DockerHub, so your please ensure
that the orchestrator environment your pipeline runs in has sufficient
permission(s) to pull images from registries if you are using one of those.

