---
description: Ensuring your pipelines or steps run on GPU-backed hardware.
---

# Scaling Compute to the Cloud

ZenML enables you to scale your pipelines or steps to run on GPU-backed hardware, ensuring that you get the performance boost you need. This can be achieved through multiple ways, such as using [step operator stack components](broken-reference/) or specifying [custom per-step or per-pipeline requirements](broken-reference/). To run steps or pipelines on GPUs, it's crucial to have the necessary CUDA tools installed in the environment. This section will guide you on how to configure your environment to utilize GPU capabilities effectively.

All steps running on GPU-backed hardware will be executed within a containerized environment, whether you're using the local Docker orchestrator or a cloud instance of Kubeflow. Therefore, you need to make two amendments to your Docker settings for the relevant steps:

## 1. **Specify a CUDA-enabled parent image in your `DockerSettings`**

For complete details, refer to the [containerization page](broken-reference/) that explains how to do this. As an example, if you want to use the latest CUDA-enabled official PyTorch image for your entire pipeline run, you can include the following code:

```python
docker_settings = DockerSettings(parent_image="pytorch/pytorch:1.12.1-cuda11.3-cudnn8-runtime")

@pipeline(settings={"docker": docker_settings})
def my_pipeline(...):
    ...
```

For TensorFlow, you might use the `tensorflow/tensorflow:latest-gpu` image, as detailed in the [official TensorFlow documentation](https://www.tensorflow.org/install/docker#gpu_support) or their [DockerHub overview](https://hub.docker.com/r/tensorflow/tensorflow).

## 2. **Add ZenML as an explicit pip requirement**

ZenML requires that ZenML itself be installed for the containers running your pipelines and steps. Therefore, you need to explicitly state that ZenML should be installed. There are several ways to specify this, but as an example, you can update the code from above as follows:

```python
docker_settings = DockerSettings(parent_image="pytorch/pytorch:1.12.1-cuda11.3-cudnn8-runtime", requirements=["zenml==0.20.5", "torchvision"])

@pipeline(settings={"docker": docker_settings})
def my_pipeline(...):
    ...
```

Adding these two extra settings options will ensure that CUDA is enabled for the specific steps that require GPU acceleration. Note that these configuration changes are **required** for the GPU hardware to be properly utilized. If you don't update the settings, your steps might run, but they will not see any boost in performance from the custom hardware.

Be cautious when choosing the image to avoid confusion when switching between local and remote environments. For example, you might have one version of PyTorch installed locally with a particular CUDA version, but when you switch to your remote stack or environment, you might be forced to use a different CUDA version.

The core cloud operators offer prebuilt Docker images that fit with their hardware. You can find more information on them here:

* [AWS](https://github.com/aws/deep-learning-containers/blob/master/available_images.md)
* [GCP](https://cloud.google.com/deep-learning-vm/docs/images)
* [Azure](https://learn.microsoft.com/en-us/azure/machine-learning/concept-prebuilt-docker-images-inference)

Not all of these images are available on DockerHub, so ensure that the orchestrator environment your pipeline runs in has sufficient permissions to pull images from registries if you are using one of those.