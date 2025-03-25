---
description: Building container images for your ML workflow.
icon: box-open
---

# Image Builders

The image builder is an essential part of most remote MLOps stacks. It is used to build container images such that your machine-learning pipelines and steps can be executed in remote environments.

### When to use it

The image builder is needed whenever other components of your stack need to build container images. Currently, this is the case for most of ZenML's remote [orchestrators](https://docs.zenml.io/stacks/orchestrators/) , [step operators](https://docs.zenml.io/stacks/step-operators/), and some [model deployers](https://docs.zenml.io/stacks/model-deployers/). These containerize your pipeline code and therefore require an image builder to build [Docker](https://www.docker.com/) images.

### Image Builder Flavors

Out of the box, ZenML comes with a `local` image builder that builds Docker images on your client machine. Additional image builders are provided by integrations:

| Image Builder                      | Flavor   | Integration | Notes                                                                    |
| ---------------------------------- | -------- | ----------- | ------------------------------------------------------------------------ |
| [LocalImageBuilder](local.md)      | `local`  | _built-in_  | Builds your Docker images locally.                                       |
| [KanikoImageBuilder](kaniko.md)    | `kaniko` | `kaniko`    | Builds your Docker images in Kubernetes using Kaniko.                    |
| [GCPImageBuilder](gcp.md)          | `gcp`    | `gcp`       | Builds your Docker images using Google Cloud Build.                      |
| [AWSImageBuilder](aws.md)          | `aws`    | `aws`       | Builds your Docker images using AWS Code Build.                          |
| [Custom Implementation](custom.md) | _custom_ |             | Extend the image builder abstraction and provide your own implementation |

If you would like to see the available flavors of image builders, you can use the command:

```shell
zenml image-builder flavor list
```

### How to use it

You don't need to directly interact with any image builder in your code. As long as the image builder that you want to use is part of your active [ZenML stack](https://docs.zenml.io/user-guides/production-guide/understand-stacks), it will be used automatically by any component that needs to build container images.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
