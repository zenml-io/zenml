---
description: >-
  Learn about ZenML Pro Hybrid SaaS deployment - balancing control with
  convenience for enterprise MLOps.
icon: building-shield
---

# Hybrid SaaS Deployment

ZenML Pro Hybrid SaaS offers the perfect balance between control and convenience. While ZenML manages user authentication and RBAC through a cloud-hosted control plane, all your data, metadata, and workspaces run securely within your own infrastructure.

{% hint style="info" %}
To learn more about Hybrid SaaS deployment, [book a call](https://www.zenml.io/book-your-demo).
{% endhint %}

## Overview

The Hybrid deployment model is designed for organizations that need to keep sensitive data and metadata within their infrastructure boundaries while still benefiting from centralized user management and simplified operations.

![ZenML Pro Hybrid SaaS deployment architecture](.gitbook/assets/cloud_architecture_scenario_1_2.png)

## Architecture

### What Runs Where

| Component | Location | Purpose |
|-----------|----------|---------|
| Pro Control Plane | ZenML Infrastructure | Manages authentication, RBAC, and global workspace coordination |
| ZenML Pro Server(s) | Your Infrastructure | Handles pipeline orchestration and execution |
| Metadata Store | Your Infrastructure | Stores all pipeline runs, model metadata, and tracking information |
| Secrets Store | Your Infrastructure | Stores all credentials and sensitive configuration |
| Compute Resources | Your infrastructure through [stacks](https://docs.zenml.io/stacks) | Executes pipeline steps and training jobs |
| Data & Artifacts | Your infrastructure through [stacks](https://docs.zenml.io/stacks) | Stores datasets, models, and pipeline artifacts |

{% hint style="success" %}
All metadata, secrets, and ML artifacts remain within your infrastructure. Only authentication and authorization data flows to the ZenML control plane.
{% endhint %}

## Key Benefits

### Enhanced Security & Compliance

All metadata stays within your infrastructure, ensuring complete data sovereignty. Credentials never leave your environment, and workspaces operate behind your security perimeter, making the deployment compatible with VPN and firewall policies.

### Centralized Governance

The hybrid model provides unified user management through a single control plane for all workspaces. Permissions are centrally managed across teams with consistent RBAC, and you only need to configure SSO integration once. Platform teams gain global visibility across all workspaces while enforcing standardized organizational policies.

### Balanced Control

You maintain full control over workspace configuration and resources while benefiting from reduced operational overhead compared to a fully self-hosted deployment. Workspace resources can be configured to specific team needs, and workspaces can be fully isolated per team, department, or entity.

### Production Ready

The control plane and UI are automatically updated and maintained by ZenML, and you get direct access to ZenML experts through professional support.

## Ideal Use Cases

Hybrid SaaS works well for regulated industries (finance, healthcare, government) with strict data residency requirements, and for organizations with centralized MLOps teams managing multiple business units. It's also a good fit for companies with existing VPN or firewall policies that restrict inbound connections, enterprises requiring audit trails of all data access within their infrastructure, teams needing customization while maintaining centralized user management, and organizations with compliance requirements mandating on-premises metadata storage.

## Architecture Details

### Network Security

Workspaces initiate outbound-only connections to the control plane, meaning no inbound connections are required to your infrastructure. This makes the deployment compatible with strict firewall policies.

Each workspace can be deployed in separate VPCs or networks, isolated per team, department, or customer. Different workspaces can be configured with different security policies and managed independently by different teams.

### Data Residency

| Data Type | Storage Location | Purpose |
|-----------|------------------|---------|
| Account metadata | Control Plane | Authentication only |
| RBAC policies | Control Plane | Authorization decisions |
| Pipeline metadata | Your Infrastructure | Run history, metrics, parameters |
| Model metadata | Your Infrastructure | Model versions, stages, annotations |
| Artifacts | Your Infrastructure | Datasets, models, visualizations |
| Secrets | Your Infrastructure | Cloud credentials, API keys |
| Logs | Your Infrastructure | Step outputs, debug information |

## Setup Process

### 1. Initial Configuration

[Book a demo](https://www.zenml.io/book-your-demo) to get started. The ZenML team will set up your organization in the control plane, establish secure communication channels, and optionally configure SSO integration.

### 2. Workspace Deployment

Deploy ZenML workspaces in your infrastructure using one of the supported deployment backends: Kubernetes (recommended, including EKS, GKE, AKS, or self-managed clusters), AWS ECS, or other container orchestration platforms.

Your infrastructure needs to provide a MySQL or PostgreSQL database, egress access to `cloud.zenml.io` for control plane communication, and compute resources for the ZenML server container.

For Kubernetes environments, we provide officially [supported Helm charts](https://artifacthub.io/packages/helm/zenml/zenml) to simplify deployment. For non-Kubernetes environments, we recommend managing the ZenML server lifecycle using infrastructure-as-code tools such as Terraform, Pulumi, or AWS CloudFormation.

## Security Documentation

For software deployed on your infrastructure, ZenML provides vulnerability assessment reports with comprehensive security analysis, a software bill of materials (SBOM) with complete dependency inventory for compliance, compliance documentation to support your security audits and certifications, and architecture review through security team consultation for deployment planning. Contact [cloud@zenml.io](mailto:cloud@zenml.io) to request security documentation.

## Monitoring & Maintenance

### Control Plane (ZenML Managed)

ZenML handles automatic updates, security patches, uptime monitoring, and backup and recovery for the control plane.

### Workspaces (Your Responsibility)

You are responsible for database maintenance and backups, workspace version updates (with ZenML guidance), infrastructure scaling, and resource monitoring.

### Support Included

Your subscription includes professional support with SLA, architecture consultation, migration assistance, and security advisory updates.

## Comparison with Other Deployments

| Feature | SaaS | Hybrid SaaS | Self-hosted |
|---------|------|-------------|-------------|
| Setup Time | Minutes | Hours to Days | Days to Weeks |
| Metadata Location | ZenML Infra | Your Infra | Your Infra |
| Secret Management | ZenML or Yours | Your Infra | Your Infra |
| User Management | ZenML Managed | ZenML Managed | Self-Managed |
| Maintenance | Zero | Workspace Only | Full Stack |
| Control | Minimal | Moderate | Complete |
| Best For | Fast start | Security + Convenience | Strictest compliance |

[Compare all deployment options →](scenarios.md)

## Migration Paths

### From ZenML OSS

You can migrate from ZenML OSS by deploying a ZenML Pro-compatible workspace in your own infrastructure, starting from your existing ZenML OSS workspace deployment if you have one. The process involves updating your Docker image to the latest Pro Hybrid image provided by ZenML, setting required environment variables according to the ZenML Pro documentation (such as `ZENML_PRO_CONTROL_PLANE_URL`, `ZENML_PRO_CONTROL_PLANE_CLIENT_ID`, secrets, and SSO configuration), and restarting your deployment to apply these changes. After that, migrate your users and teams, then run `zenml login` to authenticate via [cloud.zenml.io](https://cloud.zenml.io) and connect your SDK clients to the new workspace.

### From SaaS to Hybrid

If you're interested in migrating from ZenML Pro SaaS to a Hybrid SaaS setup, we're here to help guide you through every step of the process. Because migration paths can vary depending on your organization's size, data residency requirements, and current ZenML setup, we recommend discussing your plans with a ZenML solutions architect. [Book a migration consultation](https://www.zenml.io/book-your-demo) or email us at [cloud@zenml.io](mailto:cloud@zenml.io). Your ZenML representative will provide you with a tailored migration checklist, technical documentation, and direct support to ensure a smooth transition with minimal downtime.

### Between Workspaces

A workspace deep copy feature for migrating pipelines and artifacts between workspaces is coming soon.

## Related Resources

- [System Architecture](system-architecture.md)
- [Scenarios](scenarios.md)
- [SaaS Deployment](saas-deployment.md)
- [Self-hosted Deployment](self-hosted-deployment.md)
- [Configuration Details](configuration-details.md)
- [Upgrades and Updates](upgrades-updates.md)
- [Workspaces](workspaces.md)
- [Organizations](organization.md)

## Get Started

Ready to deploy ZenML Pro in Hybrid mode? [Book a Demo](https://www.zenml.io/book-your-demo) or [contact us](mailto:cloud@zenml.io) with questions.
