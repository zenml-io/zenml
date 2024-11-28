---
description: Taking your ZenML workflow to the next level.
---

# ☁️ Cloud guide

This section of the guide consists of easy to follow guides on how to connect the major public clouds to your ZenML deployment. We achieve this by configuring a [stack](../production-guide/understand-stacks.md).

A `stack` is the configuration of tools and infrastructure that your pipelines can run on. When you run a pipeline, ZenML performs a different series of actions depending on the stack.

<figure><img src="../../.gitbook/assets/vpc_zenml.png" alt=""><figcaption><p>ZenML is the translation layer that allows your code to run on any of your stacks</p></figcaption></figure>

Note, this guide focuses on the *registering* a stack, meaning that the resources required to run pipelines have already been *provisioned*. In order to provision the underlying infrastructure, you can either do so manually, use the [in-browser stack deployment wizard](../../how-to/infrastructure-deployment/stack-deployment/deploy-a-cloud-stack.md), the [stack registration wizard](../../how-to/infrastructure-deployment/stack-deployment/register-a-cloud-stack.md),
or [the ZenML Terraform modules](../../how-to/infrastructure-deployment/stack-deployment/deploy-a-cloud-stack-with-terraform.md).

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
