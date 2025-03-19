---
description: Learn about the ZenML Pro features and deployment scenarios.
icon: star
cover: .gitbook/assets/pro-cover.png
coverY: 0
layout:
  cover:
    visible: true
    size: hero
  title:
    visible: true
  description:
    visible: true
  tableOfContents:
    visible: true
  outline:
    visible: true
  pagination:
    visible: true
---

# Introduction

## What is ZenML Pro?

The [Pro version of ZenML](https://zenml.io/pro) comes with a number of features that expand the functionality of the Open Source product.

![Walkthrough of ZenML Model Control Plane](../../.gitbook/assets/mcp_walkthrough.gif)

ZenML Pro adds a managed control plane with benefits like:

#### **A managed production-grade ZenML deployment**

With ZenML Pro you can deploy multiple ZenML servers called [workspaces](workspaces.md).

#### **User management with teams**

Create [organizations](organization.md) and [teams](teams.md) to easily manage users at scale.

#### **Role-based access control and permissions**

Implement fine-grained access control using customizable [roles](roles.md) to ensure secure and efficient resource management.

#### **Enhanced model and artifact control plane**

Leverage the [Model Control Plane](https://docs.zenml.io/user-guides/starter-guide/track-ml-models) and [Artifact Control Plane](https://docs.zenml.io/user-guides/starter-guide/manage-artifacts) for improved tracking and management of your ML assets.

#### **Triggers and run templates**

ZenML Pro enables you to [create and run templates](https://docs.zenml.io/how-to/trigger-pipelines#run-templates). This way, you can use the dashboard or our Client/REST API to run a pipeline with updated configuration, allowing you to iterate quickly with minimal friction.

#### **Early-access features**

Get early access to pro-specific features such as triggers, filters, sorting, generating usage reports, and more.

Learn more about ZenML Pro on the [ZenML website](https://zenml.io/pro).

{% hint style="info" %}
If you're interested in assessing ZenML Pro, you can simply create\
a [free account](https://cloud.zenml.io/?utm_source=docs\&utm_medium=referral_link\&utm_campaign=cloud_promotion\&utm_content=signup_link).\
Learn more about ZenML Pro on the [ZenML website](https://zenml.io/pro).
{% endhint %}

## Deployment scenarios: SaaS vs Self-hosted

One of the most straightforward paths to start with a deployed ZenML server is to use [the SaaS version of ZenML Pro](https://zenml.io/pro). The ZenML Pro offering eliminates the need for you to dedicate time and resources to deploy and manage a ZenML server, allowing you to focus primarily on your MLOps workflows.

However, ZenML Pro can also be deployed fully self-hosted. Please [book a demo](https://www.zenml.io/book-your-demo) to learn more or check out the [self-hosted deployment guide](self-hosted.md).

## Pro Features

Explore the advanced capabilities available with ZenML Pro to manage teams, workspaces, and deployments at scale.

<table data-view="cards"><thead><tr><th></th><th></th><th data-hidden data-card-cover data-type="files"></th><th data-hidden></th><th data-hidden data-type="content-ref"></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td><strong>Workspaces</strong></td><td>Workspaces in ZenML Pro</td><td><a href=".gitbook/assets/pro-workspaces.png">pro-workspaces.png</a></td><td></td><td></td><td><a href="workspaces.md">workspaces.md</a></td></tr><tr><td><strong>Organizations</strong></td><td>Organizations in ZenML Pro</td><td><a href=".gitbook/assets/pro-organizations.png">pro-organizations.png</a></td><td></td><td></td><td><a href="organization.md">organization.md</a></td></tr><tr><td><strong>Teams</strong></td><td>Teams in ZenML Pro</td><td><a href=".gitbook/assets/pro-teams.png">pro-teams.png</a></td><td></td><td></td><td><a href="teams.md">teams.md</a></td></tr><tr><td><strong>Roles</strong></td><td>Roles in ZenML Pro</td><td><a href=".gitbook/assets/pro-roles.png">pro-roles.png</a></td><td></td><td></td><td><a href="roles.md">roles.md</a></td></tr><tr><td><strong>Self-Hosted Deployments</strong></td><td>Self-hosted ZenML Pro deployments</td><td><a href=".gitbook/assets/pro-self-host.png">pro-self-host.png</a></td><td></td><td></td><td><a href="self-hosted.md">self-hosted.md</a></td></tr></tbody></table>
