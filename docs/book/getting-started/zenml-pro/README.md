---
description: Learn about the ZenML Pro features and deployment scenarios.
cover: .gitbook/assets/procover.png
coverY: 0
layout:
  width: default
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
  metadata:
    visible: true
---

# Introduction

## What is ZenML Pro?

The [Pro version of ZenML](https://zenml.io/pro) extends the Open Source product with advanced features for enterprise-grade MLOps. It provides multi-user collaboration, role-based access control, flexible deployment options, and professional support to help teams scale their ML operations.

![Walkthrough of ZenML Model Control Plane](.gitbook/assets/mcp-walkthrough.gif)

{% hint style="info" %}
To get access to ZenML Pro, [book a call](https://www.zenml.io/book-your-demo).
{% endhint %}

## ZenML OSS vs Pro Feature Comparison

| Feature Category | ZenML OSS | ZenML Pro |
|-----------------|-----------|-----------|
| **User Management** | Single-user mode | Multi-user support with SSO, [organizations](organization.md), and [teams](teams.md) |
| **Access Control** | ❌ No RBAC | Full [role-based access control](roles.md) with customizable permissions |
| **Multi-tenancy** |  ❌ No workspaces/projects | [Workspaces](workspaces.md) and [projects](projects.md) for team and resource isolation |
| **ZenML Web UI** | Basic pipeline and run visualization | Pro UI with [Model Control Plane](https://docs.zenml.io/concepts/models), [Artifact Control Plane](https://docs.zenml.io/concepts/dashboard-features), and comparison views |
| **Pipeline Execution** | Run pipelines via SDK/CLI | Run pipelines from the UI, manage schedules through the UI, [triggers](https://docs.zenml.io/concepts/snapshots) |
| **Stack Configuration** | User-managed stacks | Advanced stack configurations with workspace/project-level restrictions for platform teams |
| **Security** | Community updates | Prioritized security patches, SOC 2 and ISO 27001 certification |
| **Deployment** | Self-hosted only | [SaaS](saas-deployment.md), [Hybrid](hybrid-deployment.md), or [Self-hosted](self-hosted-deployment.md) options |
| **Support** | Community support | Professional support included (SaaS deployments) |
| **Reporting** | Basic run tracking | Advanced usage reports and analytics |
| **Core Features** | ✅ Run pipelines on stacks<br>✅ Full observability over runs<br>✅ Artifact tracking<br> | ✅ All OSS features<br>✅ [Run Snapshots](https://docs.zenml.io/concepts/snapshots)<br>✅ Model Control Plane<br>✅ Artifact Control Plane<br>✅ Enhanced filtering and search |

## Security & Compliance

All ZenML Pro deployments include:

- ✅ **SOC 2 Type II** certification
- ✅ **ISO 27001** certification
- ✅ **Vulnerability Assessment Reports** available on request
- ✅ **Software Bill of Materials (SBOM)** available on request

## Documentation Guide

This documentation is organized to help you understand, deploy, and manage ZenML Pro:

| Section | Description |
|---------|-------------|
| [**System Architecture**](system-architecture.md) | How ZenML Pro services (Control Plane, Workspace Server, Workload Manager) communicate and interact |
| [**Scenarios**](scenarios.md) | Decision guide to help you choose between SaaS, Hybrid, and Self-hosted deployments |
| [**Deployment Details**](deploy-details.md) | Reference for configurable options, environment variables, and permissions for each component |
| [**Upgrades and Updates**](upgrades-updates.md) | How to upgrade each ZenML Pro component |
| [**Core Concepts**](hierarchy.md) | Organizations, Workspaces, Projects, Teams, and Hierarchy |
| [**Access Management**](roles.md) | Roles, Permissions, Service Accounts, and Secrets |

## Pro Feature Details

<table data-view="cards"><thead><tr><th></th><th></th><th data-hidden data-card-cover data-type="files"></th><th data-hidden></th><th data-hidden data-type="content-ref"></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td><strong>Workspaces</strong></td><td>Isolated environments for teams and projects</td><td><a href=".gitbook/assets/pro-workspaces.png">pro-workspaces.png</a></td><td></td><td></td><td><a href="workspaces.md">workspaces.md</a></td></tr><tr><td><strong>Organizations</strong></td><td>Top-level entity for managing users and teams</td><td><a href=".gitbook/assets/pro-organizations.png">pro-organizations.png</a></td><td></td><td></td><td><a href="organization.md">organization.md</a></td></tr><tr><td><strong>Teams</strong></td><td>Group users for simplified access management</td><td><a href=".gitbook/assets/pro-teams.png">pro-teams.png</a></td><td></td><td></td><td><a href="teams.md">teams.md</a></td></tr><tr><td><strong>Roles</strong></td><td>Customizable role-based access control</td><td><a href=".gitbook/assets/pro-roles.png">pro-roles.png</a></td><td></td><td></td><td><a href="roles.md">roles.md</a></td></tr><tr><td><strong>Projects</strong></td><td>Organize work within workspaces</td><td><a href=".gitbook/assets/pro-projects.png">pro-projects.png</a></td><td></td><td></td><td><a href="projects.md">projects.md</a></td></tr><tr><td><strong>Snapshots</strong></td><td>Trigger pipelines from dashboard, SDK, CLI, or REST API</td><td><a href=".gitbook/assets/pro-workload-managers.png">pro-workload-managers.png</a></td><td></td><td></td><td><a href="snapshots.md">snapshots.md</a></td></tr><tr><td><strong>Deployment Options</strong></td><td>SaaS, Hybrid, or Full On-Prem deployments</td><td><a href=".gitbook/assets/pro-self-host.png">pro-self-host.png</a></td><td></td><td></td><td><a href="scenarios.md">scenarios.md</a></td></tr></tbody></table>
