---
description: How to include ZenML in the CI/CD/CT workflows
---

# Productionalize with CI/CD/CT

In many production settings it is undesirable to have all developers accessing and running on the production environments. The concept of GitOps typically solves this issue. Here is how it could be applied in your ZenML projects.

<div>

<img src="../../assets/diagrams/Remote_with_git_ops.png" alt="">

 

<figure><img src="../../.gitbook/assets/Remote_with_git_ops.png" alt=""><figcaption><p>How to use ZenML with CI/CD frameworks</p></figcaption></figure>

</div>

You can find a code example that uses the visualized flow [here](https://github.com/zenml-io/zenml-gitflow).&#x20;

In essence this is what happens:

1\) User writes and pushes code to their code repository

2\) The CI/CD Framework of the code repository starts a worker

3\) Within this worker zenml and other requirements will be installed

4 - 6) The worker connects to the ZenML server and triggers a pipeline run

7 - 11) The pipeline is now executed on the stack of choice

