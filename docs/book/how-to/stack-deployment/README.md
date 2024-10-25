---
description: Stacks are the configuration of your infrastructure.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Managing stacks & components

The [stack](../../user-guide/production-guide/understand-stacks.md) is a fundamental component of the ZenML framework. Put simply, a stack represents the configuration of the infrastructure and tooling that defines where and how a pipeline executes.

However, deploying and managing a MLOps stack is tricky 😭😵‍💫. It is not trivial to set up all the different tools that you might need for your pipeline.

* 🌈 Each tool comes with a certain set of requirements. For example, a Kubeflow installation will require you to have a Kubernetes cluster, and so would a Seldon Core deployment.
* 🤔 Figuring out the defaults for infra parameters is not easy. Even if you have identified the backing infra that you need for a stack component, setting up reasonable defaults for parameters like instance size, CPU, memory, etc., needs a lot of experimentation to figure out.
* 🚧 Many times, standard tool installations don't work out of the box. For example, to run a custom pipeline in Vertex AI, it is not enough to just run an imported pipeline. You might also need a custom service account that is configured to perform tasks like reading secrets from your secret store or talking to other GCP services that your pipeline might need.
* 🔐 Some tools need an additional layer of installations to enable a more secure, production-grade setup. For example, a standard MLflow tracking server deployment comes without an authentication frontend which might expose all of your tracking data to the world if deployed as-is.
* 🗣️ All the components that you deploy must have the right permissions to be able to talk to each other. When you run your pipeline, it is inevitable that some components would need to communicate with the others. For example, your workloads running in a Kubernetes cluster might require access to the container registry or the code repository, and so on.
* 🧹 Cleaning up your resources after you're done with your experiments is super important yet very challenging. Many of the components need a range of other resources to work which might slide past your radar if you're not careful. For example, if your Kubernetes cluster has made use of Load Balancers, you might still have one lying around in your account even after deleting the cluster, costing you money and frustration.

All of these points make taking your pipelines to production a more difficult task than it should be. We believe that the expertise in setting up these often-complex stacks shouldn't be a prerequisite to running your ML pipelines.

This docs section consists of information that makes it easier to provision, configure, and extend stacks and components in ZenML.

<table data-view="cards">
  <thead>
    <tr>
      <th></th>
      <th></th>
      <th data-hidden data-card-target data-type="content-ref"></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><mark style="color:purple;"><strong>Deploy a cloud stack with ZenML</strong></mark></td>
      <td>Description of deploying a cloud stack with ZenML.</td>
      <td><a href="./deploy-a-cloud-stack.md">./deploy-a-cloud-stack.md</a></td>
    </tr>
    <tr>
      <td><mark style="color:purple;"><strong>Register a cloud stack</strong></mark></td>
      <td>Description of registering a cloud stack.</td>
      <td><a href="./register-a-cloud-stack.md">./register-a-cloud-stack.md</a></td>
    </tr>
    <tr>
      <td><mark style="color:purple;"><strong>Deploy a cloud stack with Terraform</strong></mark></td>
      <td>Description of deploying a cloud stack with Terraform.</td>
      <td><a href="./deploy-a-cloud-stack-with-terraform.md">./deploy-a-cloud-stack-with-terraform.md</a></td>
    </tr>
    <tr>
      <td><mark style="color:purple;"><strong>Deploy stack/components using mlstacks</strong></mark></td>
      <td>Deploying an entire stack with ZenML's `mlstacks` package.</td>
      <td><a href="./deploy-a-stack-using-mlstacks.md">./deploy-a-stack-using-mlstacks.md</a></td>
    </tr>
    <tr>
      <td><mark style="color:purple;"><strong>Reference secrets in stack configuration</strong></mark></td>
      <td>Description of referencing secrets in stack configuration.</td>
      <td><a href="./reference-secrets-in-stack-configuration.md">./reference-secrets-in-stack-configuration.md</a></td>
    </tr>
    <tr>
      <td><mark style="color:purple;"><strong>Implement a custom stack component</strong></mark></td>
      <td>Creating your custom stack component solutions.</td>
      <td><a href="./implement-a-custom-stack-component.md">./implement-a-custom-stack-component.md</a></td>
    </tr>
    <tr>
      <td><mark style="color:purple;"><strong>Implement a custom integration</strong></mark></td>
      <td>Description of implementing a custom integration.</td>
      <td><a href="./implement-a-custom-integration.md">./implement-a-custom-integration.md</a></td>
    </tr>
  </tbody>
</table>

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
