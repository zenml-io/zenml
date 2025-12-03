---
description: Learn about ZenML Pro SaaS deployment - the fastest way to get started with production-ready MLOps.
icon: cloud
---

# SaaS Deployment

ZenML Pro SaaS is the fastest and easiest way to get started with enterprise-grade MLOps. With zero infrastructure setup required, you can be running production pipelines within minutes while maintaining full control over your data and compute resources.

{% hint style="info" %}
To get access to ZenML Pro, [book a call](https://www.zenml.io/book-your-demo).
{% endhint %}

## Overview

In a SaaS deployment, ZenML manages all server infrastructure while your sensitive data and compute resources remain in your own cloud environment. This architecture provides the fastest time-to-value while maintaining data sovereignty for your ML workloads.

![ZenML Pro SaaS deployment architecture](../../.gitbook/assets/cloud_architecture_scenario_1.png)

## Architecture

### What Runs Where

| Component | Location | Purpose |
|-----------|----------|---------|
| **ZenML Server** | ZenML Infrastructure | Manages pipeline orchestration and metadata |
| **Pro Control Plane** | ZenML Infrastructure | Handles authentication, RBAC, and workspace management |
| **Metadata Store** | ZenML Infrastructure | Stores pipeline runs, model metadata, and tracking information |
| **Secrets Store** | ZenML Infrastructure (default) | Stores credentials for accessing your infrastructure |
| **Compute Resources** | Your infrastructure through [stacks](https://docs.zenml.io/stacks) | Executes pipeline steps and training jobs |
| **Data & Artifacts** | Your infrastructure through [stacks](https://docs.zenml.io/stacks) | Stores datasets, models, and pipeline artifacts |

### Data Flow

For a detailed explanation of the common pipeline execution data flow across all deployment scenarios, see [Common Pipeline Execution Data Flow](deployments-overview.md#common-pipeline-execution-data-flow) in the Deployment Scenarios Overview.

{% hint style="success" %}
**Your ML data never leaves your infrastructure.** Only metadata about runs and pipelines is stored on ZenML infrastructure.
{% endhint %}

## Key Benefits

### ⚡ Fastest Setup
- **Minutes to production**: No infrastructure provisioning required for ZenML services
- **Low maintenance**: Updates and patches handled automatically
- **Instant scaling**: Infrastructure scales with your needs

### 🛡️ Security & Compliance
- **SOC 2 Type II certified**: Enterprise-grade security controls
- **ISO 27001 certified**: International security management standards
- **Data sovereignty**: Your ML data stays in your infrastructure
- **Encrypted communications**: All data in transit is encrypted
- **Custom secret stores**: Optionally use your own secret management solution

### 🚀 Production Ready from Day 1
- **High availability**: Built-in redundancy and failover
- **Automatic backups**: Metadata backed up continuously
- **Monitoring included**: Health checks and alerting configured
- **Professional support**: Direct access to ZenML experts

### 👥 Collaboration Features
- **Multi-user support**: Full team collaboration capabilities
- **SSO integration**: Connect with your identity provider
- **Role-based access control**: Granular permissions management
- **Workspaces & projects**: Organize teams and resources

## Ideal Use Cases

ZenML Pro SaaS is perfect for:

- **Startups and scale-ups** that need production MLOps quickly without infrastructure overhead
- **Teams without dedicated DevOps** that want managed infrastructure and support
- **Organizations with existing cloud infrastructure** comfortable with SaaS tools
- **Teams prioritizing velocity** over complete infrastructure control
- **POC and pilot projects** that need to demonstrate value quickly

## Secret Management Options

### Default: ZenML-Managed Secrets Store

By default, ZenML Pro SaaS stores your cloud credentials securely in our managed secrets store. This provides:
- Zero configuration required
- Automatic encryption at rest and in transit
- Access controls via RBAC
- Audit logging of secret access

### Alternative: Customer-Managed Secrets Store

For organizations with strict security requirements, you can configure ZenML to use your own secrets management solution:
- AWS Secrets Manager
- Google Cloud Secret Manager
- Azure Key Vault
- HashiCorp Vault

![SaaS with customer secret store](../../.gitbook/assets/cloud_architecture_saas_detailed_2.png)

This keeps all credentials within your infrastructure while still benefiting from managed ZenML services - [Book a call](https://www.zenml.io/book-your-demo) with us if you want this set up.

## Network Architecture

### Outbound-Only Communication

ZenML Pro SaaS uses outbound-only connections from your infrastructure to ZenML services:
- No inbound connections required to your infrastructure
- Compatible with firewall and VPN restrictions
- Secure WebSocket connections for real-time updates

### Artifact Store Access

The ZenML dashboard requires read access to your artifact store to display:
- Pipeline visualizations
- Model comparison views
- Artifact lineage graphs
- Step logs and outputs

You control this access by configuring appropriate cloud IAM permissions.

## Getting Started

### 1. Sign Up

[Book a demo](https://www.zenml.io/book-your-demo) to get started with ZenML Pro SaaS.

### 2. Connect Your Cloud

Configure access to your cloud infrastructure:
- Set up an artifact store (S3, GCS, Azure Blob, etc.)
- Configure compute resources (AWS, GCP, Azure, or Kubernetes)
- Provide necessary credentials via secrets

### 3. You're ready to run your pipelines and monitor them through the Frontend

## Security Documentation

For software deployed on your infrastructure, ZenML provides:

- **Vulnerability Assessment Reports**: Comprehensive security analysis available on request
- **Software Bill of Materials (SBOM)**: Complete dependency inventory for compliance
- **Compliance documentation**: Support for your security audits and certifications

Contact [cloud@zenml.io](mailto:cloud@zenml.io) to request security documentation.

## Pricing & Support

ZenML Pro SaaS includes:
- Managed infrastructure and updates
- Professional support with SLA
- Regular security patches and updates
- Access to pro-exclusive features
- Usage-based pricing model

[Contact us](https://www.zenml.io/book-your-demo) for pricing details and custom plans.

## Comparison with Other Deployments

| Feature | SaaS | Hybrid SaaS | Full On-Prem |
|---------|------|-------------|------------|
| Setup Time | ⚡ Minutes | Hours | Days |
| Maintenance | Zero | Workspace only | Full stack |
| Infrastructure Control | Minimal | Moderate | Complete |
| Data Sovereignty | Metadata on ZenML | Full | Full |
| Best For | Fast time-to-value | Security requirements | Strictest compliance |

[Compare all deployment options →](README.md#deployment-scenarios-comparison)

## Migration Path

Already running ZenML OSS? Migrating to SaaS is straightforward:

1. **Export your data**: Use ZenML's migration tools
2. **Set up SaaS workspace**: Configure your cloud connections
3. **Import metadata**: Transfer existing pipeline history
4. **Update pipelines**: Point to your new ZenML server

Need help with migration? Our support team can assist.

## Detailed Architecture Diagram

<img src="../../.gitbook/assets/cloud_architecture_saas_detailed.png" alt="ZenML Pro Full SaaS deployment with ZenML secret store" data-size="original">

## Related Resources

- [System Architecture Overview](../system-architectures.md#zenml-pro-saas-architecture)
- [Deployment Scenarios Overview](deployments-overview.md)
- [Hybrid SaaS Deployment](hybrid-deployment.md)
- [Full On-Prem Deployment](air-gapped-deployment.md)
- [Workload Managers](workload-managers.md)
- [Security & Compliance](README.md#security--compliance)

## Get Started

Ready to get started with ZenML Pro SaaS?

[Book a Demo](https://www.zenml.io/book-your-demo){ .md-button .md-button--primary }

Have questions? [Contact us](mailto:cloud@zenml.io) or check out our [documentation](https://docs.zenml.io).
