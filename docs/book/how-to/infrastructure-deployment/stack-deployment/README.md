---
icon: screwdriver-wrench
description: >
  Stacks represent the infrastructure and tooling that defines where and how a pipeline executes.
---

# Managing stacks & components


## What is a stack?

The [stack](../../user-guide/production-guide/understand-stacks.md) is a fundamental component of the ZenML framework. Put simply, a stack represents the configuration of the infrastructure and tooling that defines where and how a pipeline executes.

A stack comprises different stack components, where each component is responsible for a specific task. For example, a stack might have a [container registry](../../component-guide/container-registries/container-registries.md), a [Kubernetes cluster](../../component-guide/orchestrators/kubernetes.md) as an [orchestrator](../../component-guide/orchestrators/orchestrators.md), an [artifact store](../../component-guide/artifact-stores/artifact-stores.md), an [experiment tracker](../../component-guide/experiment-trackers/experiment-trackers.md) like MLflow and so on.

## Stacks as a way to organize your execution environment

With ZenML, you can run your pipelines on more than one stacks with ease. This pattern helps you test your code across different environments effortlessly.

This enables a case like this: a data scientist starts experimentation locally on their system and then once they are satisfied, move to a cloud environment on your staging cloud account to test more advanced features of your pipeline. Finally, when all looks good, they can mark the pipeline ready for production and have it run on a production-grade stack in your production cloud account.

![Stacks as a way to organize your execution environment](../../../../docs/book/.gitbook/assets/stack_envs.png)

Having separate stacks for these environments helps:
- avoid wrongfully deploying your staging pipeline to production
- curb costs by running less powerful resources in staging and testing locally first
- control access to environments by granting permissions for only certain stacks to certain users

## How to manage credentials for your stacks

Most stack components require some form of credentials to interact with the underlying infrastructure. For example, a container registry needs to be authenticated to push and pull images, a Kubernetes cluster needs to be authenticated to deploy models as a web service, and so on.

The preferred way to handle credentials in ZenML is to use [Service Connectors](../../../../docs/book/how-to/infrastructure-deployment/auth-management/service-connectors-guide.md). Service connectors are a powerful feature of ZenML that allow you to abstract away credentials and sensitive information from your team.

![Service Connectors abstract away complexity and implement security best practices](../../.gitbook/assets/ConnectorsDiagram.png)

### Recommended roles

Ideally, you would want that only the people who deal with and have direct access to your cloud resources are the ones that are able to create Service Connectors. This is useful for a few reasons:

- **Less chance of credentials leaking**: the more people that have access to your cloud resources, the higher the chance that some of them will be leaked.
- **Instant revocation of compromised credentials**: folks who have direct access to your cloud resources can revoke the credentials instantly if they are compromised, making this a much more secure setup.
- **Easier auditing**: you can have a much easier time auditing and tracking who did what if you have a clear separation between the people who can create Service Connectors (who have direct access to your cloud resources) and those who can only use them.

### Recommended workflow

![Recommended workflow for managing credentials](../../../../docs/book/.gitbook/assets/service_con_workflow.png)

Here's an approach you can take that is a good balance between convenience and security:
- Have a limited set of people that have permissions to create Service Connectors. These are ideally people that have access to your cloud accounts and know what credentials to use.
- You can create one connector for your development or staging environment and let your data scientists use that to register their stack components.
- When you are ready to go to production, you can create another connector with permissions for your production environment and create stacks that use it. This way you can ensure that your production resources are not accidentally used for development or staging.

If you follow this approach, you can keep your data scientists free from the hassle of figuring out the best authentication mechanisms for the different cloud services, having to manage credentials locally, and keep your cloud accounts safe, while still giving them the freedom to run their experiments in the cloud.

{% hint style="info" %}

Please note that restricting permissions for users through roles is a ZenML Pro feature. You can read more about it [here](../../../../docs/book/getting-started/zenml-pro/roles.md). Sign up for a free trial here: https://cloud.zenml.io/.

{% endhint %}


## How to deploy and manage stacks

Deploying and managing a MLOps stack is tricky.

* Each tool comes with a certain set of requirements. For example, a [Kubeflow installation](https://www.kubeflow.org/docs/started/installing-kubeflow/) will require you to have a Kubernetes cluster, and so would a **Seldon Core deployment**.
* Figuring out the defaults for infra parameters is not easy. Even if you have identified the backing infra that you need for a stack component, setting up reasonable defaults for parameters like instance size, CPU, memory, etc., needs a lot of experimentation to figure out.
* Many times, standard tool installations don't work out of the box. For example, to run a custom pipeline in [Vertex AI](https://cloud.google.com/vertex-ai), it is not enough to just run an imported pipeline. You might also need a custom service account that is configured to perform tasks like reading secrets from your secret store or talking to other GCP services that your pipeline might need.
* Some tools need an additional layer of installations to enable a more secure, production-grade setup. For example, a standard **MLflow tracking server** deployment comes without an authentication frontend which might expose all of your tracking data to the world if deployed as-is.
* All the components that you deploy must have the right permissions to be able to talk to each other. For example, your workloads running in a Kubernetes cluster might require access to the container registry or the code repository, and so on.
* Cleaning up your resources after you're done with your experiments is super important yet very challenging. For example, if your Kubernetes cluster has made use of [Load Balancers](https://kubernetes.io/docs/concepts/services-networking/service/#loadbalancer), you might still have one lying around in your account even after deleting the cluster, costing you money and frustration.

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
