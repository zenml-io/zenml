---
description: Using Docker images to run your pipeline.
---

# 🐳 Customize docker builds

ZenML executes pipeline steps sequentially in the active Python environment when running locally. However, with remote [orchestrators](../../configure-stack-components/orchestrators/README.md) or [step operators](../../configure-stack-components/step-operators/README.md), ZenML builds [Docker](https://www.docker.com/) images to run your pipeline in an isolated, well-defined environment.

This section discusses how to control this dockerization process.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>