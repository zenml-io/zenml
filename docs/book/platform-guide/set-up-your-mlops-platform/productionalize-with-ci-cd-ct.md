---
description: How to include ZenML in the CI/CD/CT workflows
---

# Productionalize with CI/CD/CT

In many production settings it is undesirable to have all developers accessing and running on the production environments. Instead, this is typically centralized through the means of git ops.&#x20;

<div>

<img src="../../assets/diagrams/Remote_with_git_ops.png" alt="">

 

<figure><img src="../../.gitbook/assets/Remote_with_git_ops.png" alt=""><figcaption><p>How to use ZenML with CI/CD frameworks</p></figcaption></figure>

</div>

This same principle can be easily used for pipeline deployments using ZenML. The architecture diagram above visualizes how a pipeline would be run through an automated action that is triggered when new code is pushed to the main code repository.

You can find an example of this [here](https://github.com/zenml-io/zenml-gitflow).
