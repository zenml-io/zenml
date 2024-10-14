---
description: Different variations of the ZenML architecture depending on your needs.
---

# System Architectures

{% hint style="info" %}
If you're interested in assessing ZenML Pro, you can create
a [free account](https://cloud.zenml.io/?utm\_source=docs\&utm\_medium=referral\_link\&utm\_campaign=cloud\_promotion\&utm\_content=signup\_link),
which defaults to a [Scenario 1](./#scenario-1-full-saas) deployment. To upgrade
to different scenarios, please [reach out to us](mailto:cloud@zenml.io).
{% endhint %}

The ZenML Pro offers many additional features to increase your teams
productivity. No matter your specific needs, the hosting options for ZenML Pro
range from easy SaaS integration to completely airgapped deployments on your own
infrastructure.

A [ZenML Pro deployment](./zenml-pro.md) consists of the following moving pieces for both the SaaS
product as well as the self-hosted version.:

* **ZenML Pro Control Plane**: This is a centralized MLOps control plane that includes a
  managed ZenML dashboard and a special ZenML server optimized for production
  MLOps workloads.
* **Single Sign-On (SSO)**: The ZenML Pro API is integrated
  with [Auth0](https://auth0.com/) as an SSO provider to manage user
  authentication and authorization. Users can log in to the ZenML Pro
  app using their social media accounts or their corporate credentials.
* **Secrets Store**: All secrets and credentials required to access customer
  infrastructure services are stored in a secure secrets store. The ZenML Pro
  API has access to these secrets and uses them to access customer
  infrastructure services on behalf of the ZenML Pro. The secrets store can be
  hosted either by the ZenML Pro or by the customer.
* **ML Metadata Store**: This is where all ZenML metadata is stored, including
  ML metadata such as tracking and versioning information about pipelines and
  models.

## Deployment Scenarios

The above four interact with other MLOps stack components, secrets, and data in
the two scenarios described below.

### Scenario 1: Full SaaS

![Scenario 1: Full SaaS deployment](../../.gitbook/assets/cloud_architecture_scenario_1.png)


In this scenario, all services are hosted on infrastructure hosted by the ZenML Team,
except the MLOps stack components.
Customer secrets and credentials required to access customer infrastructure are
stored and managed by the ZenML Pro Control Plane.

On the ZenML Pro infrastructure, only ML _metadata_ (e.g. pipeline and
model tracking and versioning information) is stored. All the actual ML data
artifacts (e.g. data produced or consumed by pipeline steps, logs and
visualizations, models) are stored on the customer cloud. This can be set up
quite easily by configuring
an [artifact store](../../component-guide/artifact-stores/artifact-stores.md)
with your MLOps stack.

Your tenant only needs permissions to read from this data to display artifacts
on the ZenML dashboard. The tenant also needs direct access to parts of the
customer infrastructure services to support dashboard control plane features
such as CI/CD, triggering and running pipelines, triggering model deployments
etc.

This scenario is meant for customers who want to quickly get started with ZenML
and can to a certain extent allow ingress connections into their infrastructure
from an external SaaS provider.

{% hint style="info" %}
We also offer a hybrid SaaS option where customer secrets are stored on the
customer side. In this case, the customer connects their own
secret store directly to the ZenML server that is managed by us. All ZenML
secrets used by running pipelines to access infrastructure services and
resources are stored in the customer secret store. This allows users to
use [service connectors](../../how-to/auth-management/service-connectors-guide.md)
and the [secrets API](../../how-to/interact-with-secrets.md) to authenticate
ZenML pipelines and the ZenML Pro to 3rd party services and infrastructure
while ensuring that credentials are always stored on the customer side.
{% endhint %}


## Scenario 2: Fully On-prem

![Scenario 2: Fully on-premises deployment](../../.gitbook/assets/cloud_architecture_scenario_2.png)

In this scenario, all services, data, and secrets are deployed on the customer
cloud. This is the opposite of Scenario 1, and is meant for customers who
require completely airgapped deployments, for the tightest security standards. 
[Reach out to us](mailto:cloud@zenml.io) if you want to set this up.

Are you interested in ZenML Pro? [Sign up](https://cloud.zenml.io/?utm\_source=docs\&utm\_medium=referral\_link\&utm\_campaign=cloud\_promotion\&utm\_content=signup\_link)
and get access to Scenario 1. with a free 14 day trial now!

## ZenML Pro vs ZenML Open Source

TODO: add diagram + feature differences
also more on architectural distinctions

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
