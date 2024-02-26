---
description: Different variations of the ZenML Cloud architecture depending on your needs.
---

# System Architecture

{% hint style="info" %}
If you're interested in assessing ZenML Cloud, you can create a [free account](https://cloud.zenml.io/?utm_source=docs&utm_medium=referral_link&utm_campaign=cloud_promotion&utm_content=signup_link), which defaults to a [Scenario 1](#scenario-1-full-saas) deployment. To upgrade to different scenarios, please [reach out to us](mailto:cloud@zenml.io).
{% endhint %}

Machine learning often involves data that is sensitive and thus data security is a fundamental requirement. The ZenML Cloud is flexible enough to meet your security requirements, from easy installations to completely airgapped deployments.

The ZenML Cloud consists of the following moving pieces:

* **ZenML Cloud API**: This is a centralized MLOps control plane that includes a managed ZenML dashboard and a special ZenML server optimized for production MLOps workloads.
* **Single Sign-On (SSO)**: The ZenML Cloud API is integrated with [Auth0](https://auth0.com/) as an SSO provider to manage user authentication and authorization. Users can log in to the ZenML Cloud dashboard using their social media accounts or their corporate credentials.
* **Secrets Store**: All secrets and credentials required to access customer infrastructure services are stored in a secure secrets store. The ZenML Cloud API has access to these secrets and uses them to access customer infrastructure services on behalf of the ZenML Cloud. The secrets store can be hosted either by the ZenML Cloud or by the customer.
* **ML Metadata Store**: This is where all ZenML metadata is stored, including ML metadata such as tracking and versioning information about pipelines and models.
* **ZenML Cloud Agent (Optional)**: This service is optionally deployed customer-side, and interacts with customer MLOps stack components on behalf of the remote ZenML Cloud control plane.

The above five interact with other MLOps stack components, secrets, and data in varying scenarios described below.

## Scenario 1: Full SaaS

<div data-full-width="true">

<figure><img src="../../.gitbook/assets/cloud_architecture_scenario_1.png" alt=""><figcaption><p>Scenario 1: Full SaaS deployment</p></figcaption></figure>

</div>

In this scenario, all services are hosted on the ZenML Cloud infrastructure. Customer secrets and credentials required to access customer infrastructure are stored and managed by the ZenML Cloud.

The ZenML Cloud only stores ML _metadata_ (e.g. pipeline and model tracking and versioning information). All the actual ML data artifacts (e.g. data produced or consumed by pipeline steps, logs and visualizations, models) are stored on the customer cloud. This can be set up quite easily by configuring an [artifact store](../../stacks-and-components/component-guide/artifact-stores/) with your MLOps stack. The ZenML Cloud only needs permissions to read from this data to display artifacts on the ZenML dashboard. The ZenML Cloud also needs direct access to parts of the customer infrastructure services to support dashboard control plane features such as CI/CD, triggering and running pipelines, triggering model deployments etc.

This scenario is meant for customers who want to quickly get started with ZenML Cloud and can to a certain extent allow ingress connections into their infrastructure from an external SaaS provider.

## Scenario 2: Hybrid SaaS with Customer Secret Store managed by ZenML

<div data-full-width="true">

<figure><img src="../../.gitbook/assets/cloud_architecture_scenario_2.png" alt=""><figcaption><p>Scenario 2: Hybrid SaaS with Customer Secret Store managed by ZenML</p></figcaption></figure>

</div>

This scenario is a version of Scenario 1. modified to store all sensitive information on the customer side. In this case, the customer connects their own secret store directly to the ZenML Cloud. All ZenML secrets used by running pipelines to access infrastructure services and resources are stored in the customer secret store. This allows users to use [service connectors](../../stacks-and-components/auth-management/service-connectors-guide.md) and the [secrets API](../../user-guide/advanced-guide/secret-management/) to authenticate ZenML pipelines and the ZenML Cloud to 3rd party services and infrastructure while ensuring that credentials are always stored on the customer side.

Even though they are stored customer side, access to ZenML secrets is fully managed by the ZenML Cloud. The ZenML Cloud is also allowed to use some of those credentials to connect directly to customer infrastructure services to implement control plane features such as artifact visualization or triggering pipelines. This implies that the secret values are allowed to leave the customer environment to allow their access to be managed centrally by the ZenML Cloud and to enforce access control policies, but the ZenML users and pipelines never have direct access to the secret store.

All access to customer secrets is, of course, regulated through authentication and RBAC, so that only authorized users can access the secrets. This deployment scenario is meant for customers who want to use the ZenML Cloud but want to keep their secrets on their own infrastructure.

## Scenario 3: Agent Architecture

<div data-full-width="true">

<figure><img src="../../.gitbook/assets/cloud_architecture_scenario_3 (1).png" alt=""><figcaption><p>Scenario 3: ZenML Agent deployment</p></figcaption></figure>

</div>

This scenario adds a new architectural component into the mix, called the ZenML Agent, which facilitates communication between the two clouds. The customer is responsible for deploying and maintaining the ZenML Agent in their environment. The agent acts as an intermediate step for all operations and information that needs to be exchanged between ZenML cloud and other customer stack components, like the artifact store. This means that all features like visualizing data artifacts in the dashboard and triggering pipelines from the dashboard are fully available, but only the ZenML Agent has access to customer secrets and accesses the customer's infrastructure services.

The advantage of this deployment is that the ZenML Cloud does not need direct access to any sensitive secrets to trigger actions customer-side. The ZenML Agent executes all operations that require access to secrets or customer infrastructure on behalf of the ZenML Cloud. Secrets and data remain on the customer environment, and only one secure ingress connection is established.

Here is a concrete example of how this works:

* The ZenML Cloud API asks the agent to fetch an artifact for visualization.
* The agent connects to the S3 bucket directly with the credentials configured by the customer and stored in the customer secret store or via a service connector.
* Credentials never have to leave the agent.
* The agent fetches the artifact and sends it back to the Cloud API.
* The Cloud API sends the visualization to the dashboard.

## Scenario 4: Fully On-prem

<div data-full-width="true">

<figure><img src="../../.gitbook/assets/cloud_architecture_scenario_4 (1).png" alt=""><figcaption><p>Scenario 4: Fully on-premises deployment</p></figcaption></figure>

</div>

In this scenario, all services, data, and secrets are deployed on the customer cloud. This is the opposite of Scenario 1, and is meant for customers who require completely airgapped deployments, for the tightest security standards.

Are you interested in the ZenML Cloud? While in beta, we're looking for early adopters to talk to! [Sign up](https://cloud.zenml.io/?utm_source=docs&utm_medium=referral_link&utm_campaign=cloud_promotion&utm_content=signup_link) and get access to Scenario 1. with a free 30 day trial now!

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
