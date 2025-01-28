---
icon: box-open
description: Building container images for your ML workflow.
---

# Image Builders

The image builder is an essential part of most remote MLOps stacks. It is used to build container images such that your
machine-learning pipelines and steps can be executed in remote environments.

### When to use it

The image builder is needed whenever other components of your stack need to build container images. Currently, this is
the case for most of ZenML's remote [orchestrators](../orchestrators/orchestrators.md)
, [step operators](../step-operators/step-operators.md), and
some [model deployers](../model-deployers/model-deployers.md). These containerize your pipeline code and therefore
require an image builder to build [Docker](https://www.docker.com/) images.

### Image Builder Flavors

Out of the box, ZenML comes with a `local` image builder that builds Docker images on your client machine. Additional
image builders are provided by integrations:

| Image Builder                      | Flavor   | Integration | Notes                                                                    |
|------------------------------------|----------|-------------|--------------------------------------------------------------------------|
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

You don't need to directly interact with any image builder in your code. As long as the image builder that you want to
use is part of your active [ZenML stack](/docs/book/user-guide/production-guide/understand-stacks.md), it will be used
automatically by any component that needs to build container images.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
