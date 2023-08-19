---
description: Different variations of the ZenML Cloud architecture depending on your needs.
---

# ☁ Cloud Architecture

{% hint style="info" %}
ZenML Cloud is currently in the beta phase, offering users the opportunity to host a managed ZenML instance and gain early access to the exciting new features mentioned above. Beta users will receive priority access to the enhanced functionalities and dedicated support to ensure a smooth onboarding experience. 

[Let us know on Slack](https://zenml.io/slack) if you would like to see other deployment scenarios with ZenML Cloud.
{% endhint %}

Machine learning often involves data that is sensitive and thus data security is a fundamental requirement. The ZenML Cloud is flexible enough to meet any security requirements, from easy installations to completely airgapped deployments.

The ZenML Cloud consists of the following moving pieces:

* ZenML Cloud API: This is a centralized MLOps control plane that includes a managed ZenML dashboard and a special ZenML server optimized for production MLOps workloads.

* MLflow Tracking Server: This is an optional add-on with ZenML Cloud that features a MLflow tracking server with detached artifact storage.

* ZenML Cloud Agent: This service is optionally deployed customer side, and interacts with customer MLOps stack components on behalf of the remote ZenML Cloud control plane.

The above three interact with other MLOps stack components, secrets, and data in varying scenarios described below.

{% hint style="info" %}
In this phase, the scenarios below are experimental and subject to change. For now, Scenario 2a is used by default when you [sign up for ZenML Cloud](https://cloud.zenml.io). For other scenarios, [contact us on Slack](https://zenml.io/slack).
{% endhint %}

## Scenario 1: Fully SaaS

<div data-full-width="true">
<figure><img src="../../.gitbook/assets/cloud_architecture_scenario_1.png" alt=""><figcaption><p>Scenario 1: Fully SaaS deployment</p></figcaption></figure>
</div>

In this scenario, all services are hosted on the ZenML Cloud infrastructure. The ZenML Cloud API and MLflow Tracking store secrets and data on the ZenML side. The Cloud API interact with the customer cloud for certain actions like triggering pipelines, deploying models etc.

This scenario is meant for customers who want to get started quickly with ZenML Cloud and can to a certain extend expose ingress connections to an external SaaS provider. 

## Scenario 2a: Hybrid SaaS

<div data-full-width="true">
<figure><img src="../../.gitbook/assets/cloud_architecture_scenario_2a.png" alt=""><figcaption><p>Scenario 2a: Hybrid SaaS deployment</p></figcaption></figure>
</div>

## Scenario 2b: Hybrid SaaS + Private Secret Store

<div data-full-width="true">
<figure><img src="../../.gitbook/assets/cloud_architecture_scenario_2b.png" alt=""><figcaption><p>Scenario 2a: Hybrid SaaS deployment + Private Secret Store</p></figcaption></figure>
</div>

## Scenario 3: Agent Architecture

<div data-full-width="true">
<figure><img src="../../.gitbook/assets/cloud_architecture_scenario_3.png" alt=""><figcaption><p>Scenario 3: ZenML Agent deployment</p></figcaption></figure>
</div>

## Scenario 4: Fully On-prem

<div data-full-width="true">
<figure><img src="../../.gitbook/assets/cloud_architecture_scenario_4.png" alt=""><figcaption><p>Scenario 4: Fully on-premises deployment</p></figcaption></figure>
</div>
