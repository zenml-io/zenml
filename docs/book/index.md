---
description: Simple MLOps.
---

# Introduction

{% hint style="warning" %}
**IMPORTANT NOTICE**: As of **April 8th, 2021**, we are migrating and reworking our docs for a better developer experience. We expect the migration to be complete by **April 15th.**

During the migration, you might experience broken links, images and more. We apologize for the inconvenience. Please bear with us as we make the docs a better developer experience for you. Thank you!
{% endhint %}

**ZenML** is an extensible, open-source MLOps framework for using production-ready Machine Learning pipelines, in a simple way. At its core, ZenML will orchestrate your experiment pipelines from **sourcing data** to **splitting, preprocessing, training**, all the way to the **evaluation of results** and even **serving**.

While there are other pipelining solutions for Machine Learning experiments, ZenML is focused on the following:

* Simplicity.
* [Reproducibility](https://github.com/maiot-io/zenml/tree/9c7429befb9a99f21f92d13deee005306bd06d66/docs/book/benefits/ensuring-ml-reproducibility.md). 
* [Integrations](https://github.com/maiot-io/zenml/tree/c2dd7d85740f8f992ad5ea7ac7cd89a8805c5e6a/docs/book/repository/integration-with-git.md).

## Why do I need ZenML?

ZenML solves the problem of getting Machine Learning in models. You should use ZenML if you struggle with:

* **Reproducing** training results in production.
* Managing ML **metadata**, including data, code, and model versioning.
* Getting \(and keeping\) ML models in **production**.
* **Reusing** code/data and reducing waste.
* Maintaining **comparability** between ML models.
* **Scaling ML** training/inference to large datasets.
* Retaining code **quality** alongside development velocity.
* Keeping up with the ML **tooling landscape** in a coherent manner.

## Awesome things you can do with ZenML

* Reproduce experiments at any time, on any environment. \[[here's how](https://github.com/maiot-io/zenml/tree/9c7429befb9a99f21f92d13deee005306bd06d66/docs/book/benefits/ensuring-ml-reproducibility.md)\].
* Automatically track all parameters when creating ML experiments. \[[here's how](https://github.com/maiot-io/zenml/tree/9c7429befb9a99f21f92d13deee005306bd06d66/docs/book/tutorials/creating-first-pipeline.ipynb)\].
* Collaborate with your team using a git repo, re-use code, share results and compare experiments. \[[here's how](https://github.com/maiot-io/zenml/tree/c2dd7d85740f8f992ad5ea7ac7cd89a8805c5e6a/docs/book/tutorials/team-collaboration-with-zenml-and-google-cloud.md)\].
* No-hassle preprocessing and training on big VM's on the, for 1/4th the price. \[[here's how](https://github.com/maiot-io/zenml/tree/c2dd7d85740f8f992ad5ea7ac7cd89a8805c5e6a/docs/book/tutorials/running-a-pipeline-on-a-google-cloud-vm.md)\].
* Distribute preprocessing on hundreds of workers for millions of datapoints. \[[here's how](https://github.com/maiot-io/zenml/tree/c2dd7d85740f8f992ad5ea7ac7cd89a8805c5e6a/docs/book/tutorials/building-a-classifier-on-33m-samples.md)\].
* Launching training jobs on GPUs on the cloud with a simple command. \[[here's how](https://github.com/maiot-io/zenml/tree/main/examples/gcp_gpu_training)\].
* No-hassle evaluation of models with slicing metrics. \[[here's how](https://github.com/maiot-io/zenml/tree/9c7429befb9a99f21f92d13deee005306bd06d66/docs/book/tutorials/creating-first-pipeline.ipynb)\]. 
* Instantly deploy a model to the cloud. \[[here's how](https://github.com/maiot-io/zenml/tree/main/examples/gcp_gcaip_deployment)\].
* De-couple infrastructure from ML code. \[[here's how](https://github.com/maiot-io/zenml/tree/c2dd7d85740f8f992ad5ea7ac7cd89a8805c5e6a/docs/book/backends/what-is-a-backend.md)\].

## What do I do next?

If one of the above links are too hands-on, then a good place to go from this point is:

* Get up and running with your first pipeline [with the Quickstart](starter-guide/quickstart.md).
* Read more about [core concepts](core-concepts.md) to inform your decision about using ZenML.
* Check out how to [convert your old ML code](https://github.com/maiot-io/zenml/tree/835d32fc4f6d33eb691f0e8311720240e7fa51d1/docs/book/getting-started/organizing-zenml.md) into ZenML pipelines, or start from scratch with our [tutorials](https://github.com/maiot-io/zenml/tree/9c7429befb9a99f21f92d13deee005306bd06d66/docs/book/tutorials/creating-first-pipeline.ipynb)
* If you are working as a team, see how to [collaborate using ZenML in a team setting](https://github.com/maiot-io/zenml/tree/835d32fc4f6d33eb691f0e8311720240e7fa51d1/docs/book/repository/team-collaboration-with-zenml.md).

## Get involved

If you're just not ready to use ZenML for whatever reason, but still would like to stay updated, then the best way is to [star the GitHub repository](https://github.com/maiot-io/zenml)! You can then keep up with the latest going-on's of ZenML, and it would help us tremendously to get more people using it.

Contributions are also welcome! Please read out [contributing guide](https://github.com/maiot-io/zenml/blob/main/CONTRIBUTING.md) to get started.

