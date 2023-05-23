---
description: Deploying your stack components directly from the ZenML CLI
---

# Deploy & set up a cloud stack

The first step in running your pipelines on remote infrastructure is to deploy all the components that you would need, like an MLflow tracking server, a Seldon Core model deployer, and more to your cloud.&#x20;

However, we believe that the expertise in setting up these often-complex stacks shouldn't be a prerequisite to running your ML pipelines. We have created the `deploy` CLI to allow you to quickly get started with a full-fledged MLOps stack with just a few commands. You can choose to deploy individual stack components through the stack-component CLI or deploy a stack with multiple components together (a tad more manual steps) using _stack recipes._&#x20;

<table data-view="cards"><thead><tr><th></th><th></th><th data-hidden></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td><mark style="color:purple;"><strong>Deploy stack components individually</strong></mark></td><td>Individually deploying different stack components.</td><td></td><td><a href="broken-reference">Broken link</a></td></tr><tr><td><mark style="color:purple;"><strong>Deploy a stack with multiple components using Stack Recipes</strong></mark></td><td>Deploying an entire stack with the ZenML Stack Recipes.</td><td></td><td><a href="deploy-a-stack-using-stack-recipes.md">deploy-a-stack-using-stack-recipes.md</a></td></tr><tr><td><mark style="color:purple;"><strong>Contribute new components or flavors</strong></mark></td><td>Creating your custom stack component solutions.</td><td></td><td><a href="contribute-flavors-or-components.md">contribute-flavors-or-components.md</a></td></tr></tbody></table>

##

