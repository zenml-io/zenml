---
description: Deploying your stack components directly from the ZenML CLI
---

# Deploy and set up a cloud stack

The first step in running your pipelines on remote infrastructure is to deploy all the components that you would need, like an MLflow tracking server, a Seldon Core model deployer and more to your cloud.&#x20;

However, we believe that the expertise of setting up these often-complex stacks shouldn't be a prerequisite to running your ML pipelines. We have created the `deploy` CLI to allow you to quickly get started with a full-fledged MLOps stack with just a few commands. You can choose to deploy individual stack components through the stack-component CLI, or deploy a stack with multiple components together (a tad more manual steps) using _stack recipes._&#x20;

<table data-view="cards"><thead><tr><th></th><th></th><th></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td></td><td>Deploying Stack Components Individually (Recommended)</td><td></td><td><a href="deploying-stack-components.md">deploying-stack-components.md</a></td></tr><tr><td></td><td></td><td>Deploying a Stack with multiple components using Stack Recipes</td><td><a href="deploying-a-stack-using-stack-recipes.md">deploying-a-stack-using-stack-recipes.md</a></td></tr><tr><td></td><td></td><td>Contributing new components or flavors</td><td><a href="contributing-flavors-or-components.md">contributing-flavors-or-components.md</a></td></tr></tbody></table>

##

