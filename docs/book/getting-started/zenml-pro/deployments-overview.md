---
description: Compare ZenML Pro deployment scenarios to find the right fit for your organization.
icon: code-merge
layout:
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

# Deployment Scenarios

ZenML Pro offers three flexible deployment options to match your organization's security, compliance, and operational needs. This page helps you understand the differences and choose the right scenario for your use case.

## Quick Comparison

| Deployment Aspect | Purpose | SaaS | Hybrid SaaS | Self-hosted |
|-------------------|---------|------|-------------|-------------|
| **ZenML Server** | Stores pipeline metadata and serves the API that your SDK and UI connect to | ZenML infrastructure | Your infrastructure | Your infrastructure |
| **Pipeline/ Artifact Metadata** | Records of your pipeline runs, step executions, and artifact locations | ZenML infrastructure | Your infrastructure | Your infrastructure |
| **ZenML Control Plane** | Manages authentication, RBAC, and organization-level settings across workspaces | ZenML infrastructure | ZenML infrastructure | Your infrastructure |
| **ZenML Pro UI** | Web UI for visualizing pipelines, artifacts, and managing your ML workflows | ZenML infrastructure | ZenML infrastructure | Your infrastructure |
| **Compute & Data** | Your ML training infrastructure, models, datasets, and artifacts | Your infrastructure | Your infrastructure | Your infrastructure |
| **Setup Time** | Time to get your first pipeline running | ⚡ ~1 hour | ~4 hours | ~8 hours |
| **Maintenance** | Ongoing operational responsibility | Fully managed | Partially managed (workspace maintenance required) | Customer managed |
| **Best For** | Recommended use case | Teams wanting minimal infrastructure overhead and fastest time-to-value | Organizations with security/compliance requirements but wanting simplified user management | Organizations requiring complete data isolation and on-premises control |

{% hint style="info" %}
In all of these cases the client sdk that you pip install into your development environment is the same one found here: https://pypi.org/project/zenml/
{% endhint %}

## Which Scenario is Right for You?

### SaaS Deployment

Choose **SaaS** if you want to get started immediately with zero infrastructure overhead.

**What runs where:**
- ZenML Server: ZenML infrastructure
- Metadata and RBAC: ZenML infrastructure
- Compute and Data: Your infrastructure

**Key Benefits:**
- ⚡ Fastest setup (minutes)
- ✅ Fully managed by ZenML
- 🚀 Immediate production readiness
- 💰 Minimal operational overhead

**Ideal for:** Startups, teams prioritizing time-to-value and operational simplicity, organizations comfortable leveraging managed cloud services.

[Learn more about SaaS deployment →](saas-deployment.md)

### Hybrid SaaS Deployment

Choose **Hybrid** if you need to keep sensitive metadata in your infrastructure while benefiting from centralized user management.

**What runs where:**
- ZenML Control Plane: ZenML infrastructure
- ZenML Pro UI: ZenML infrastructure
- ZenML Pro Server: Your infrastructure
- Run metadata: Your infrastructure
- Compute and Data: Your infrastructure

**Key Benefits:**
- 🔐 Metadata stays in your infrastructure
- 👥 Centralized user management
- ⚖️ Balance of control and convenience
- 🏢 Control plane and UI fully maintained and patched by ZenML
- ✅ Day 1 production ready

**Ideal for:** Organizations with security policies requiring metadata sovereignty, teams wanting simplified identity management without full infrastructure control.

[Learn more about Hybrid deployment →](hybrid-deployment.md)

### Self-hosted Deployment

Choose **Self-hosted** if you need complete control with no external dependencies.

**What runs where:**
- All components: Your infrastructure (completely isolated)

**Key Benefits:**
- 🔒 Complete data sovereignty
- 🚫 No external network dependencies
- 🛡️ Maximum security posture

**Ideal for:** Regulated industries (healthcare, finance, defense), government organizations, enterprises with strict data residency requirements, environments requiring offline operation.

[Learn more about Self-hosted deployment →](self-hosted-deployment.md)

### Deployment-Specific Differences

All three deployment scenarios follow the same [pipeline execution data flow](services.md#pipeline-execution-data-flow), with differences in where authentication happens and where data resides:

**SaaS**: Metadata is stored in ZenML infrastructure. Your ML data and compute remain in your infrastructure.

**Hybrid**: Metadata and control plane are split — authentication/RBAC happens at ZenML control plane, but all run metadata, artifacts, and compute stay in your infrastructure.

**Self-hosted**: All components (control plane, metadata, authentication, compute) run entirely within your infrastructure with zero external dependencies.

## Making Your Choice

Consider these factors when deciding:

1. **Data Location Requirements**: Where must your ML metadata and run data reside?
   - Cloud-hosted is acceptable → **SaaS**
   - Must stay in your infrastructure → **Hybrid**
   - Must be completely isolated on-premises → **Self-hosted**

2. **Infrastructure Complexity**: How much infrastructure control do you want?
   - Minimal → **SaaS**
   - Moderate → **Hybrid**
   - Full control → **Self-hosted**

3. **Time to Value**: How quickly do you need to be productive?
   - Within 1 hour → **SaaS**
   - Within 4 hours → **Hybrid**
   - Within 8 hours (or longer planning period) → **Self-hosted**

4. **Compliance Requirements**: What regulations apply to your organization?
   - General business → **SaaS**
   - Data residency rules → **Hybrid**
   - Strict isolation requirements → **Self-hosted**

## Security & Compliance

All ZenML Pro deployments include:

- ✅ **SOC 2 Type II** certification
- ✅ **ISO 27001** certification
- ✅ **Vulnerability Assessment Reports** available on request
- ✅ **Software Bill of Materials (SBOM)** available on request

For software deployed on your infrastructure (Hybrid and Self-hosted scenarios), ZenML provides comprehensive security documentation to support your compliance requirements.

## Running Pipelines from the web UI

All deployment scenarios support running pipeline snapshots from the UI through [workload managers](workload-managers.md). Workload managers are built into the ZenML Pro workspace and can be configured to orchestrate pipeline execution on your Kubernetes cluster, AWS ECS, or GCP infrastructure.

Learn more: [Understanding Workload Managers](workload-managers.md)

## Next Steps

- **Ready to start?** [Choose SaaS Deployment](saas-deployment.md)
- **Need metadata control?** [Set up Hybrid Deployment](hybrid-deployment.md)
- **Require complete isolation?** [Configure Self-hosted Deployment](self-hosted-deployment.md)
- **Deploying on your own infrastructure?** [See Self-hosted Deployment Guide](self-hosted.md)
- **Want to run pipelines from the UI?** [Configure Workload Managers](workload-managers.md)

{% hint style="info" %}
Not sure which option is right for you? [Book a call](https://www.zenml.io/book-your-demo) with our team to discuss your specific requirements.
{% endhint %}
