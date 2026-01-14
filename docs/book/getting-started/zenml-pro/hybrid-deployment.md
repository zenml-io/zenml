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
| **Pro Control Plane** | ZenML Infrastructure | Manages authentication, RBAC, and global workspace coordination |
| **ZenML Pro Server(s)** | Your Infrastructure | Handles pipeline orchestration and execution |
| **Metadata Store** | Your Infrastructure | Stores all pipeline runs, model metadata, and tracking information |
| **Secrets Store** | Your Infrastructure | Stores all credentials and sensitive configuration |
| **Compute Resources** | Your infrastructure through [stacks](https://docs.zenml.io/stacks) | Executes pipeline steps and training jobs |
| **Data & Artifacts** | Your infrastructure through [stacks](https://docs.zenml.io/stacks) | Stores datasets, models, and pipeline artifacts |



{% hint style="success" %}
**Complete data sovereignty**: All metadata, secrets, and ML artifacts remain within your infrastructure. Only authentication and authorization data flows to ZenML control plane.
{% endhint %}

## Key Benefits

### Enhanced Security & Compliance

* Data sovereignty - All metadata stay within your infrastructure
* Secret isolation - Credentials never leave your environment
* VPN/Firewall compatible - Workspaces operate behind your security perimeter


### Centralized Governance

* Unified user management - Single control plane for all workspaces
* Consistent RBAC - Centrally managed permissions across teams
* SSO integration - Connect with your identity provider once
* Global visibility - Platform teams see across all workspaces
* Standardized policies - Enforce organizational standards

### Balanced Control

* Infrastructure control - Full control over workspace configuration and resources
* Reduced operational overhead (compared to self-hosted)
* Customization freedom - Configure workspace resources to specific team needs
* Network isolation - Workspaces can be fully isolated per team/department/entitiy

### Production Ready

* Automatic updates - Control plane and UI maintained by ZenML
* Professional support - Direct access to ZenML experts

## Ideal Use Cases

Hybrid SaaS is perfect for:

* **Regulated industries** (finance, healthcare, government) with strict data residency requirements
* **Organizations with centralized MLOps teams** managing multiple business units
* **Companies with existing VPN/firewall policies** that restrict inbound connections
* **Enterprises requiring audit trails** of all data access within their infrastructure
* **Teams needing customization** while maintaining centralized user management
* **Organizations with compliance requirements** mandating on-premises metadata storage

## Architecture Details

### Network Security

#### Outbound-Only Connections

Workspaces initiate outbound-only connections to the control plane:

* No inbound connections required to your infrastructure
* Compatible with strict firewall policies

#### Multi-Workspace Isolation

Each workspace can be:

* Deployed in separate VPCs/networks
* Isolated per team or department or customer
* Configured with different security policies
* Managed independently by different teams

### Data Residency

| Data Type         | Storage Location    | Purpose                             |
| ----------------- | ------------------- | ----------------------------------- |
| User metadata     | Control Plane       | Authentication only                 |
| RBAC policies     | Control Plane       | Authorization decisions             |
| Pipeline metadata | Your Infrastructure | Run history, metrics, parameters    |
| Model metadata    | Your Infrastructure | Model versions, stages, annotations |
| Artifacts         | Your Infrastructure | Datasets, models, visualizations    |
| Secrets           | Your Infrastructure | Cloud credentials, API keys         |
| Logs              | Your Infrastructure | Step outputs, debug information     |

## Setup Process

### 1. Initial Configuration

[Book a demo](https://www.zenml.io/book-your-demo) to get started. The ZenML team will:

* Set up your organization in the control plane
* Establish secure communication channels
* (optional) Configure SSO integration

### 2. Workspace Deployment

Deploy ZenML workspaces in your infrastructure. Workspaces can be deployed on:

**Supported Deployment Backends:**

* **Kubernetes** (Recommended) - EKS, GKE, AKS, or self-managed clusters
* **AWS ECS** - Elastic Container Service
* **Container orchestration alternatives** - Other Kubernetes distributions

**Requirements:**

* **Database**: MySQL or PostgreSQL database in your infrastructure
* **Network**: Egress access to `cloud.zenml.io` (for Control Plane communication)
* **Resources**: Compute resources for the ZenML server container

**Deployment Tools:**

For Kubernetes environments, we provide officially [supported Helm charts](https://artifacthub.io/packages/helm/zenml/zenml) to simplify deployment. If you are deploying to a non-Kubernetes environment, we recommend managing the ZenML server lifecycle using infrastructure-as-code tools such as Terraform, Pulumi, or AWS CloudFormation.

## Security Documentation

For software deployed on your infrastructure, ZenML provides:

* **Vulnerability Assessment Reports**: Comprehensive security analysis available on request
* **Software Bill of Materials (SBOM)**: Complete dependency inventory for compliance
* **Compliance documentation**: Support for your security audits and certifications
* **Architecture review**: Security team consultation for deployment planning

Contact [cloud@zenml.io](mailto:cloud@zenml.io) to request security documentation.

## Monitoring & Maintenance

### Control Plane (ZenML Managed)

* ✅ Automatic updates
* ✅ Security patches
* ✅ Uptime monitoring
* ✅ Backup and recovery

### Workspaces (Your Responsibility)

* Database maintenance and backups
* Workspace version updates (with ZenML guidance)
* Infrastructure scaling
* Resource monitoring

### Support Included

* Professional support with SLA
* Architecture consultation
* Migration assistance
* Security advisory updates

## Comparison with Other Deployments

| Feature           | SaaS           | Hybrid SaaS            | Self-hosted          |
| ----------------- | -------------- | ---------------------- | -------------------- |
| Setup Time        | Minutes        | Hours to Days          | Days to Weeks        |
| Metadata Location | ZenML Infra    | Your Infra             | Your Infra           |
| Secret Management | ZenML or Yours | Your Infra             | Your Infra           |
| User Management   | ZenML Managed  | ZenML Managed          | Self-Managed         |
| Maintenance       | Zero           | Workspace Only         | Full Stack           |
| Control           | Minimal        | Moderate               | Complete             |
| Best For          | Fast start     | Security + Convenience | Strictest compliance |

[Compare all deployment options →](scenarios.md)

## Migration Paths

### From ZenML OSS

1. Deploy a ZenML Pro-compatible workspace in your own infrastructure (you can start from your existing ZenML OSS workspace deployment).
   * **Update your Docker image**: Replace the OSS ZenML server image with the latest Pro Hybrid image provided by ZenML.
   * **Set required environment variables**: Add or update environment variables according to the ZenML Pro documentation (for example: `ZENML_PRO_CONTROL_PLANE_URL`, `ZENML_PRO_CONTROL_PLANE_CLIENT_ID`, secrets, and SSO configuration as instructed by ZenML).
   * **Restart your deployment** to apply these changes.
2. Migrate users and teams
3. Run `zenml login` to authenticate via [cloud.zenml.io](https://cloud.zenml.io) and connect your SDK clients to the new workspace

### From SaaS to Hybrid

If you're interested in migrating from the ZenML Pro SaaS deployment to a Hybrid SaaS setup, we're here to help guide you through every step of the process. Because migration paths can vary depending on your organization’s size, data residency requirements, and current ZenML setup, we recommend discussing your plans with a ZenML solutions architect.

**Next steps:**

* [Book a migration consultation →](https://www.zenml.io/book-your-demo)
* Or email us at [cloud@zenml.io](mailto:cloud@zenml.io)

Your ZenML representative will provide you with a tailored migration checklist, technical documentation, and direct support to ensure a smooth transition with minimal downtime.

### Between Workspaces

A workspace deep copy feature for migrating pipelines and artifacts between workspaces is coming soon.

## Detailed Architecture Diagram

![ZenML Pro Hybrid SaaS detailed architecture](.gitbook/assets/cloud_architecture_scenario_1_2.png)

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

Ready to deploy ZenML Pro in Hybrid mode?

[Book a Demo](https://www.zenml.io/book-your-demo){ .md-button .md-button--primary }

Have questions? [Contact us](mailto:cloud@zenml.io) or check out our [documentation](https://docs.zenml.io).
