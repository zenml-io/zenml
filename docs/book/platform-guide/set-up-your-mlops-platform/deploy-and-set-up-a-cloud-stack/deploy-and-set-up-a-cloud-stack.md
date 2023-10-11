---
description: Deploying your stack components directly from the ZenML CLI
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Deploy & set up a cloud stack

The first step in running your pipelines on remote infrastructure is to deploy all the components that you would need, like an MLflow tracking server, a Seldon Core model deployer, and more to your cloud.

This can bring plenty of benefits like scalability, reliability, and collaboration. ZenML eases the path to production by providing a seamless way for all tools to interact with others through the use of abstractions. However, one of the most painful parts of this process, from what we see on our Slack and in general, is the deployment of these stack components.

## Deploying MLOps tools is tricky 😭😵‍💫

It is not trivial to set up all the different tools that you might need for your pipeline.

* 🌈 Each tool comes with a certain set of requirements. For example, a Kubeflow installation will require you to have a Kubernetes cluster, and so would a Seldon Core deployment.
* 🤔 Figuring out the defaults for infra parameters is not easy. Even if you have identified the backing infra that you need for a stack component, setting up reasonable defaults for parameters like instance size, CPU, memory, etc., needs a lot of experimentation to figure out.
* 🚧 Many times, standard tool installations don't work out of the box. For example, to run a custom pipeline in Vertex AI, it is not enough to just run an imported pipeline. You might also need a custom service account that is configured to perform tasks like reading secrets from your secret store or talking to other GCP services that your pipeline might need.
* 🔐 Some tools need an additional layer of installations to enable a more secure, production-grade setup. For example, a standard MLflow tracking server deployment comes without an authentication frontend which might expose all of your tracking data to the world if deployed as-is.
* 🗣️ All the components that you deploy must have the right permissions to be able to talk to each other. When you run your pipeline, it is inevitable that some components would need to communicate with the others. For example, your workloads running in a Kubernetes cluster might require access to the container registry or the secrets manager, and so on.
* 🧹 Cleaning up your resources after you're done with your experiments is super important yet very challenging. Many of the components need a range of other resources to work which might slide past your radar if you're not careful. For example, if your Kubernetes cluster has made use of Load Balancers, you might still have one lying around in your account even after deleting the cluster, costing you money and frustration.

All of these points make taking your pipelines to production a more difficult task than it should be. We believe that the expertise in setting up these often-complex stacks shouldn't be a prerequisite to running your ML pipelines.

Thus to make even this process easier for our users, we have created the `deploy` CLI which allows you to quickly get started with a full-fledged MLOps stack using only a few commands. You can choose to deploy individual stack components through the stack-component CLI or deploy a stack with multiple components together (a tad more manual steps) using \_ stack recipes.\_

<table data-view="cards"><thead><tr><th></th><th></th><th data-hidden></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td><mark style="color:purple;"><strong>Deploy stack components individually</strong></mark></td><td>Individually deploying different stack components.</td><td></td><td><a href="deploy-a-stack-component.md">deploy-a-stack-component.md</a></td></tr><tr><td><mark style="color:purple;"><strong>Deploy a stack with multiple components using Stack Recipes</strong></mark></td><td>Deploying an entire stack with the ZenML Stack Recipes.</td><td></td><td><a href="deploy-a-stack-using-stack-recipes.md">deploy-a-stack-using-stack-recipes.md</a></td></tr><tr><td><mark style="color:purple;"><strong>Contribute new components or flavors</strong></mark></td><td>Creating your custom stack component solutions.</td><td></td><td><a href="contribute-flavors-or-components.md">contribute-flavors-or-components.md</a></td></tr></tbody></table>

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
