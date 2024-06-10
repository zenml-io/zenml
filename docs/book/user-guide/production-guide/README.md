---
description: Level up your skills in a production setting.
---

# 🐔 Production guide

The ZenML production guide builds upon the [Starter guide](../starter-guide/README.md) and is the next step in the MLOps Engineer journey with ZenML. If you're an ML practitioner hoping to implement a proof of concept within your workplace to showcase the importance of MLOps, this is the place for you.

<figure><img src="../../.gitbook/assets/stack_showcase.png" alt=""><figcaption><p>ZenML simplifies development of MLOps pipelines that can span multiple production stacks.</p></figcaption></figure>

This guide will focus on shifting gears from running pipelines _locally_ on your machine, to running them in _production_ in the cloud. We'll cover:

* [Deploying ZenML](deploying-zenml.md)
* [Understanding stacks](understand-stacks.md)
* [Connecting remote storage](remote-storage.md)
* [Orchestrating on the cloud](cloud-orchestration.md)
* [Configuring the pipeline to scale compute](configure-pipeline.md)
* [Configure a code repository](connect-code-repository.md)

Like in the starter guide, make sure you have a Python environment ready and `virtualenv` installed to follow along with ease. As now we are dealing with cloud infrastructure, you'll also want to select one of the major cloud providers (AWS, GCP, Azure), and make sure the respective CLIs are installed and authorized.

By the end, you will have completed an [end-to-end](end-to-end.md) MLOps project that you can use as inspiration for your own work. Let's get right into it!

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
