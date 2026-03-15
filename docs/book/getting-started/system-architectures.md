---
description: Different variations of the ZenML architecture depending on your needs.
icon: building-columns
---

# System Architecture

This guide walks through the various ways that ZenML can be deployed, from self-hosted OSS to\
SaaS to self-hosted ZenML Pro!

## ZenML OSS (Self-hosted)

{% hint style="info" %}
This page is intended as a high-level overview. To learn more about how to deploy ZenML OSS, read [this guide](deploying-zenml/).
{% endhint %}

A ZenML OSS deployment consists of the following moving pieces:

* **ZenML OSS Server**: This is a FastAPI app that manages metadata of pipelines, artifacts, stacks, etc. Note: In ZenML Pro, the notion of a ZenML server is replaced with what is known as a "Workspace". For all intents and purposes, consider a ZenML Workspace to be a ZenML OSS server that comes with more functionality.
* **OSS Metadata Store**: This is where all ZenML workspace metadata is stored, including ML metadata such as tracking and versioning information about pipelines and models.
* **OSS Dashboard**: This is a ReactJS app that shows pipelines, runs, etc.
* **Secrets Store**: All secrets and credentials required to access customer infrastructure services are stored in a secure secrets store. The ZenML Pro API has access to these secrets and uses them to access customer infrastructure services on behalf of the ZenML Pro. The secrets store can be hosted either by the ZenML Pro or by the customer.

![ZenML OSS server deployment architecture](../.gitbook/assets/oss_simple_deployment.png)

ZenML OSS is free with Apache 2.0 license. Learn how to deploy it [here](deploying-zenml/).

{% hint style="info" %}
To learn more about the core concepts for ZenML OSS, go [here](core-concepts.md).
{% endhint %}

## ZenML Pro (SaaS or Self-hosted)

{% hint style="info" %}
If you're interested in assessing ZenML Pro SaaS, you can create a [free account](https://zenml.io/pro?utm_source=docs\&utm_medium=referral_link\&utm_campaign=cloud_promotion\&utm_content=signup_link).

If you would like to self-host ZenML Pro, please [book a demo](https://zenml.io/book-a-demo).
{% endhint %}

The above deployment can be augmented with the ZenML Pro components:

* **ZenML Pro Control Plane**: This is the central controlling entity of all workspaces.
* **Pro Dashboard**: This is a dashboard that builds on top of the OSS dashboard and adds further functionality.
* **Pro Metadata Store**: This is a PostgreSQL database where all ZenML Pro-related metadata is stored, such as roles, permissions, teams, and workspace management-related data.
* **Pro Add-ons**: These are Python modules injected into the OSS Server for enhanced functionality.
* **Identity Provider**: ZenML Pro offers flexible authentication options. In cloud-hosted deployments, it integrates with [Auth0](https://auth0.com/), allowing users to log in via social media or corporate credentials. For self-hosted deployments, customers can configure their own identity management solution, with ZenML Pro supporting custom OIDC provider integration. This allows organizations to leverage their existing identity infrastructure for authentication and authorization, whether using the cloud service or deploying on-premises.

![ZenML Pro deployment architecture](../.gitbook/assets/pro_deployment_simple.png)

ZenML Pro offers many additional features to increase your team's productivity. No matter your specific needs, the hosting options for ZenML Pro range from easy SaaS integration to completely air-gapped deployments on your own infrastructure.

You might have noticed that this architecture builds on top of the ZenML OSS system architecture. Therefore, if you already have ZenML OSS deployed, it is easy to enroll it as part of a ZenML Pro deployment!

The above components interact with other MLOps stack components, secrets, and data in the following scenarios described below.

{% hint style="info" %}
To learn more about the core concepts for ZenML Pro, go [here](https://docs.zenml.io/pro/core-concepts)
{% endhint %}

### ZenML Pro SaaS Architecture

![ZenML Pro SaaS deployment with ZenML secret store](../.gitbook/assets/cloud_architecture_scenario_1.avif)

For the ZenML Pro SaaS deployment case, all ZenML services are hosted on infrastructure hosted by the ZenML Team. Customer secrets and credentials required to access customer infrastructure are stored and managed by the ZenML Pro Control Plane.

On the ZenML Pro infrastructure, only ML _metadata_ (e.g. pipeline and model tracking and versioning information) is stored. All the actual ML data artifacts (e.g. data produced or consumed by pipeline steps, logs and visualizations, models) are stored on the customer cloud. This can be set up quite easily by configuring an [artifact store](https://docs.zenml.io/stacks/artifact-stores) with your MLOps stack.

Your workspace only needs permissions to read from this data to display artifacts on the ZenML dashboard. The workspace also needs direct access to parts of the customer infrastructure services to support dashboard control plane features such as CI/CD, triggering and running pipelines, triggering model deployments and so on.

The advantage of this setup is that it is a fully-managed service, and is very easy to get started with. However, for some clients, even some metadata can be sensitive; these clients should refer to the other architecture diagram.


### ZenML Pro Hybrid SaaS

![ZenML Pro self-hosted deployment](../.gitbook/assets/cloud_architecture_scenario_1_2.avif)

The partially self-hosted architecture offers a balanced approach that combines the benefits of cloud-hosted control with on-premises data sovereignty. In this configuration, while the ZenML Pro control plane remains hosted by ZenML (handling user management, authentication, RBAC and global workspace coordination), all other components - including services, data, and secrets - are deployed within your own cloud infrastructure.

This hybrid model is particularly well-suited for organizations with:
* A centralized MLOps or Platform team responsible for standardizing ML practices
* Multiple business units or teams that require autonomy over their data and infrastructure
* Strict security requirements where workspaces must operate behind VPN/corporate firewalls
* Compliance requirements that mandate keeping sensitive data and ML artifact metadata within company infrastructure
* Need for customization of workspace configurations while maintaining centralized governance

The key advantages of this setup include:
* Simplified user management through the ZenML-hosted control plane
* Complete data sovereignty - sensitive data and ML artifacts remain within your infrastructure
* Secure networking - workspaces communicate through outbound-only connections via VPN/private networks
* Ability to customize and configure workspaces according to specific team needs
* Reduced operational overhead compared to fully self-hosted deployments
* Reduced maintenance burden - all control plane updates and maintenance are handled by ZenML
This architecture strikes a balance between convenience and control, making it a popular choice for enterprises looking to standardize their MLOps practices while maintaining sovereignty.


### ZenML Pro Self-Hosted Architecture

![ZenML Pro self-hosted deployment](../.gitbook/assets/cloud_architecture_scenario_2.avif)

In the case of self-hosting ZenML Pro, all services, data, and secrets are deployed on the customer\
cloud. This is meant for customers who require completely air-gapped deployments, for the tightest security standards. [Reach out to us](mailto:cloud@zenml.io) if you want to set this up.

<details>

<summary>Detailed Architecture Diagram for self-hosted ZenML Pro deployment</summary>

<img src="../.gitbook/assets/cloud_architecture_self_hosted_detailed (1).png" alt="ZenML Pro self-hosted deployment details" data-size="original">

</details>

Are you interested in ZenML Pro? [Sign up](https://zenml.io/pro/?utm_source=docs\&utm_medium=referral_link\&utm_campaign=cloud_promotion\&utm_content=signup_link) and get access with a free trial now!

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>


## Data Implications Across Deployment Scenarios

| Deployment Scenario | Data Location | Data Movement | Data Access | Data Isolation |
|---------------------|---------------|---------------|-------------|----------------|
| **ZenML OSS (Self-hosted)** | All data remains on customer infrastructure: both ML metadata in OSS Metadata Store and actual ML data artifacts in customer Artifact Store | Data stays within customer boundary; moves between pipeline steps via the Orchestrator | Accessible only through customer infrastructure; no ZenML-managed components have access | Complete data isolation from ZenML-managed services |
| **ZenML Pro SaaS** | ML metadata in ZenML-hosted DB; Actual ML data artifacts in customer Artifact Store; Secrets in ZenML-managed Secret Store | Metadata flows to ZenML Pro Control Plane; ML data artifacts stay on customer infrastructure; ZenML services access customer infrastructure using stored credentials | ZenML Pro has access to the customer secrets that are explicitly stored; Workspace optionally needs read access to artifact store for dashboard display; No actual ML data moves to ZenML infrastructure unless explicitly shared | Only metadata and credentials are stored on ZenML infrastructure; actual ML data remains isolated on customer infrastructure |
| **ZenML Pro Hybrid SaaS** | Control Plane on ZenML infrastructure; Workspace, DB, Secret Store, Orchestrator, and Artifact Store on customer infrastructure | Only authentication/authorization data flows to ZenML; All ML data and metadata stays on customer infrastructure | ZenML Control Plane has limited access to user management data; No access to actual ML data or metadata; Customer maintains all data access controls | Strong data isolation with only authentication events crossing boundary. Allows securing access via VPN/private networks. |
| **ZenML Pro Self-Hosted** | All components run on customer infrastructure | All data movement contained within customer infrastructure boundary | No external access to any data; completely air-gapped operation possible | Complete data isolation; ZenML has no access to any customer data |\n\n## Key Data Security Insights\n\n1. **Artifact Storage:** In all scenarios, the actual ML data artifacts (datasets, models, etc.) remain on customer infrastructure in the customer-controlled Artifact Store.\n\n2. **Metadata Storage:** The metadata (pipeline configurations, run information, metrics) is either stored in ZenML-managed databases (SaaS options) or customer-managed databases (self-hosted options).\n\n3. **Secret Management:** Credentials can be managed by ZenML (standard SaaS) or by the customer (hybrid SaaS or self-hosted), providing flexibility based on security requirements.\n\n4. **Data Access Patterns:**\n   - The ZenML Workspace frontend requires read access to the Artifact Store to display artifacts in the dashboard\n   - The Orchestrator requires read/write access to the Artifact Store to execute pipelines\n   - Control Plane DB contains only users, roles, and workspace configuration information\n\n5. **Data Isolation:** Even in the fully-managed SaaS scenario, the actual ML data never leaves customer infrastructure unless explicitly configured to do so. Only metadata about runs, pipelines, etc. is stored in ZenML-managed systems.\n\nThis design ensures that even when using ZenML-managed services, customers maintain control over their sensitive ML data while benefiting from ZenML's orchestration and management capabilities.