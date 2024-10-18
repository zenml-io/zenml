---
description: Different variations of the ZenML architecture depending on your needs.
---

# 🏛️ System Architecture

This guide walks through the various ways that ZenML can be deployed, from self-hosted OSS, to
SaaS, to self-hosted ZenML Pro!

## ZenML OSS (Self-hosted)

{% hint style="info" %}
This page is intended as a high level overview. To learn more about how about to deploy ZenML OSS,
read [this guide](../getting-started/deploying-zenml/README.md).
{% endhint %}

A ZenML OSS deployment (AKA a tenant) consists of the following moving pieces:

* **ZenML OSS Server**: This is a FastAPI app that manages metadata of pipelines, artifacts, stacks etc.
  Note: In ZenML Pro, the notion of a ZenML server is replaced with so-called "Tenant". For
  all intents and purposes, consider a ZenML Tenant == ZenML OSS server + more functionality. 
* **OSS Metadata Store**: This is where all ZenML tenant metadata is stored, including
  ML metadata such as tracking and versioning information about pipelines and
  models.
* **OSS Dashboard**: This is a ReactJS app that shows pipelines, runs, etc.
* **Secrets Store**: All secrets and credentials required to access customer
  infrastructure services are stored in a secure secrets store. The ZenML Pro
  API has access to these secrets and uses them to access customer
  infrastructure services on behalf of the ZenML Pro. The secrets store can be
  hosted either by the ZenML Pro or by the customer.

![ZenML OSS server deployment architecture](../.gitbook/assets/oss_simple_deployment.png)

ZenML OSS is free with Apache 2.0 license. Learn how to deploy it [here](./deploying-zenml/README.md).

{% hint style="info" %}
To learn more about the core concepts for ZenML OSS, go [here](../getting-started/core-concepts.md)
{% endhint %}

## ZenML Pro (SaaS or Self-hosted)

{% hint style="info" %}
If you're interested in assessing ZenML Pro SaaSs, you can create
a [free account](https://cloud.zenml.io/?utm\_source=docs\&utm\_medium=referral\_link\&utm\_campaign=cloud\_promotion\&utm\_content=signup\_link).

If would like to self-host ZenML Pro, please [book a demo](https://zenml.io/book-a-demo).
{% endhint %}

The above deployment can be augmented with the ZenML Pro components:

* **ZenML Pro Control Plane**: This is the central controlling entity of all tenants.
* **Pro Dashboard**: This is a dashboard that builds on top of the OSS dashboard, and
add further functionality.
* **Pro Metadata Store**: This is a PostgreSQL database where all ZenML Pro related metadata is stored such
as roles, permissions, teams, and tenant management related data.
* **Pro Add-ons**: These are Python modules injected into the OSS Server for enhanced functionality.
* **Identity Provider**: ZenML Pro offers flexible authentication options.
  In cloud-hosted deployments, it integrates with [Auth0](https://auth0.com/),
  allowing users to log in via social media or corporate credentials.
  For self-hosted deployments, customers can configure their
  own identity management solution, with ZenML Pro supporting
  custom OIDC provider integration. This allows organizations to
  leverage their existing identity infrastructure for authentication
  and authorization, whether using the cloud service or deploying on-premises.

![ZenML Pro deployment architecture](../.gitbook/assets/pro_deployment_simple.png)

ZenML Pro offers many additional features to increase your teams
productivity. No matter your specific needs, the hosting options for ZenML Pro
range from easy SaaS integration to completely air-gapped deployments on your own
infrastructure.

You might have noticed this architecture builds on top of the ZenML OSS system architecture.
Therefore, if you already have ZenML OSS deployed, it is easy to enroll it as part of a
ZenML Pro deployment!

The above components interact with other MLOps stack components, secrets, and data in
the following scenarios described below.

{% hint style="info" %}
To learn more about the core concepts for ZenML Pro, go [here](../getting-started/zenml-pro/core-concepts.md)
{% endhint %}

### ZenML Pro SaaS Architecture

![ZenML Pro SaaS deployment with ZenML secret store](../.gitbook/assets/cloud_architecture_scenario_1.png)

In this scenario, all ZenML services are hosted on infrastructure hosted by the ZenML Team.
Customer secrets and credentials required to access customer infrastructure are
stored and managed by the ZenML Pro Control Plane.

On the ZenML Pro infrastructure, only ML _metadata_ (e.g. pipeline and
model tracking and versioning information) is stored. All the actual ML data
artifacts (e.g. data produced or consumed by pipeline steps, logs and
visualizations, models) are stored on the customer cloud. This can be set up
quite easily by configuring
an [artifact store](../component-guide/artifact-stores/artifact-stores.md)
with your MLOps stack.

Your tenant only needs permissions to read from this data to display artifacts
on the ZenML dashboard. The tenant also needs direct access to parts of the
customer infrastructure services to support dashboard control plane features
such as CI/CD, triggering and running pipelines, triggering model deployments
etc.

The advantage of this setup is that it is a fully-managed service, and is
very easy to get started with. However, for some clients even some metadata
can be sensitive: These clients should refer to the other architecture diagram.

<details>

<summary>Detailed Architecture Diagram for SaaS deployment</summary>

<figure><img src="../.gitbook/assets/cloud_architecture_saas_detailed.png" alt="ZenML Pro Full SaaS deployment"><figcaption>ZenML Pro Full SaaS deployment with ZenML secret store</figcaption></figure>

</details>

We also offer a hybrid SaaS option where customer secrets are stored on the
customer side. In this case, the customer connects their own
secret store directly to the ZenML server that is managed by us. All ZenML
secrets used by running pipelines to access infrastructure services and
resources are stored in the customer secret store. This allows users to
use [service connectors](../how-to/auth-management/service-connectors-guide.md)
and the [secrets API](../how-to/interact-with-secrets.md) to authenticate
ZenML pipelines and the ZenML Pro to 3rd party services and infrastructure
while ensuring that credentials are always stored on the customer side.
{% endhint %}

![ZenML Pro SaaS deployment with Customer secret store](../.gitbook/assets/cloud_architecture_scenario_1_1.png)

<details>

<summary>Detailed Architecture Diagram for SaaS deployment with custom secret store configuration</summary>

<figure><img src="../.gitbook/assets/cloud_architecture_saas_detailed_2.png" alt="ZenML Pro Full SaaS deployment with custom secret store"><figcaption>ZenML Pro Full SaaS deployment with customer secret store</figcaption></figure>

</details>

### ZenML Pro Self-Hosted Architecture

![ZenML Pro self-hosted deployment](../.gitbook/assets/cloud_architecture_scenario_2.png)

In this scenario, all services, data, and secrets are deployed on the customer
cloud. This is the opposite of Scenario 1, and is meant for customers who
require completely airgapped deployments, for the tightest security standards. 
[Reach out to us](mailto:cloud@zenml.io) if you want to set this up.

<details>

<summary>Detailed Architecture Diagram for self-hosted ZenML Pro deployment</summary>

<figure><img src="../.gitbook/assets/cloud_architecture_self_hosted_detailed.png" alt="ZenML Pro self-hosted deployment details"><figcaption>ZenML Pro self-hosted deployment details</figcaption></figure>

</details>

Are you interested in ZenML Pro? [Sign up](https://cloud.zenml.io/?utm\_source=docs\&utm\_medium=referral\_link\&utm\_campaign=cloud\_promotion\&utm\_content=signup\_link)
and get access to Scenario 1. with a free 14 day trial now!

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
