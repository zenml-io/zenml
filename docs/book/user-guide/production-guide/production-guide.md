---
description: Level up your skills in a production setting.
---

# 🐣 Production guide

The ZenML production guide builds upon the [Starter guide](../starter-guide/) and is the next step in the MLOps Engineer journey with ZenML. If you're a ML practitioner hoping to implement a proof of concept within your workplace to showcase the importance of MLOps, this is the place for you.

<figure><img src="../../.gitbook/assets/stack_showcase.png" alt=""><figcaption><p>ZenML simplifies development of MLOps pipelines that can span multiple production stacks.</p></figcaption></figure>

This guide will focus on shifting gears from running pipelines *locally* on your machine, to running them in *production* in the cloud. We'll cover:

- [Connecting to a deployed ZenML server](connect-deployed-zenml.md)
- [Understanding stacks](understand-stacks.md)
- [Deploy a cloud stack](cloud-stack.md)
- [Configure a code repository](connect-code-repository.md)
- [Scale compute to the cloud](scale-compute.md)
- [Configuring your pipeline](configure-pipeline.md)

Like in the starter guide, make sure you have a Python environment ready and `virtualenv` installed to follow along with ease. As now we are dealing with cloud infrastructure, you'll also want to select one of the major cloud providers (AWS, GCP, Azure), and make sure the respective CLI's are installed and authorized.

By the end, you will have completed a [end to end](end-to-end.md) MLOps project, that you can use as inspiration for your own work. Let's get right into it!

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>