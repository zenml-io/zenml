---
description: Defining the image builder.
---

# 🐳 Define where an image is built

ZenML executes pipeline steps sequentially in the active Python environment when running locally. However, with remote [orchestrators](../../component-guide/orchestrators/orchestrators.md) or [step operators](../../component-guide/step-operators/step-operators.md), ZenML builds [Docker](https://www.docker.com/) images to run your pipeline in an isolated, well-defined environment.

By default, execution environments are created locally in the client environment using the local Docker client. However, this requires Docker installation and permissions. ZenML offers [image builders](../../component-guide/image-builders/image-builders.md), a special [stack component](../../component-guide/README.md), allowing users to build and push Docker images in a different specialized _image builder environment_.

Note that even if you don't configure an image builder in your stack, ZenML still uses the [local image builder](../../../component-guide/image-builders/local.md) to retain consistency across all builds. In this case, the image builder environment is the same as the [client environment](../pipeline-development/configure-python-environments/README.md#client-environment-or-the-runner-environment).

You don't need to directly interact with any image builder in your code. As long as the image builder that you want to
use is part of your active [ZenML stack](/docs/book/user-guide/production-guide/understand-stacks.md), it will be used
automatically by any component that needs to build container images.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
