---
description: Compare ZenML Pro deployment scenarios to find the right fit for your organization.
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

| Deployment Aspect | SaaS | Hybrid SaaS | Air-gapped |
|-------------------|------|-------------|------------|
| **ZenML Server** | ZenML infrastructure | Your infrastructure | Your infrastructure |
| **Control Plane** | ZenML infrastructure | ZenML infrastructure | Your infrastructure |
| **Metadata & RBAC** | ZenML infrastructure | RBAC: ZenML infrastructure<br>Run metadata: Your infrastructure | Your infrastructure |
| **Compute & Data** | [Your infrastructure](https://docs.zenml.io/stacks) | [Your infrastructure](https://docs.zenml.io/stacks) | [Your infrastructure](https://docs.zenml.io/stacks) |
| **Setup Time** | ⚡ ~1 hour | ~4 hours | ~8 hours |
| **Maintenance** | ✅ Fully managed | Partially managed (workspace maintenance required) | Customer managed |
| **Best For** | Teams wanting minimal infrastructure overhead and fastest time-to-value | Organizations with security/compliance requirements but wanting simplified user management | Organizations requiring complete data isolation and air-gapped environments |

## Which Scenario is Right for You?

### SaaS Deployment

Choose **SaaS** if you want to get started immediately with zero infrastructure overhead.

**What runs where:**
- ZenML Server: ZenML infrastructure
- Metadata and RBAC: ZenML infrastructure
- Compute and Data: [Your infrastructure](https://docs.zenml.io/stacks)

**Key Benefits:**
- ⚡ Fastest setup (minutes)
- ✅ Fully managed by ZenML
- 🚀 Immediate production readiness
- 💰 Minimal operational overhead

**Ideal for:** Startups, teams with high trust in ZenML infrastructure, organizations prioritizing speed-to-value over infrastructure control.

[Learn more about SaaS deployment →](saas-deployment.md)

### Hybrid SaaS Deployment

Choose **Hybrid** if you need to keep sensitive metadata in your infrastructure while benefiting from centralized user management.

**What runs where:**
- ZenML Management Plane: ZenML infrastructure
- ZenML Server: Your infrastructure
- RBAC: ZenML infrastructure
- Run metadata: Your infrastructure
- Compute and Data: [Your infrastructure](https://docs.zenml.io/stacks)

**Key Benefits:**
- 🔐 Metadata stays in your infrastructure
- 👥 Centralized user management
- ⚖️ Balance of control and convenience
- ✅ Day 1 production ready

**Ideal for:** Organizations with security policies requiring metadata sovereignty, teams wanting simplified identity management without full infrastructure control.

[Learn more about Hybrid deployment →](hybrid-deployment.md)

### Air-gapped Deployment

Choose **Air-gapped** if you need complete control with no external dependencies.

**What runs where:**
- All components: [Your infrastructure](https://docs.zenml.io/stacks) (completely isolated)

**Key Benefits:**
- 🔒 Complete data sovereignty
- 🚫 No external network dependencies
- 🛡️ Maximum security posture
- 📋 Full audit trail control

**Ideal for:** Regulated industries (healthcare, finance), government organizations, enterprises with strict data residency requirements, environments requiring offline operation.

[Learn more about Air-gapped deployment →](air-gapped-deployment.md)

## Making Your Choice

Consider these factors when deciding:

1. **Data Location Requirements**: Where must your ML metadata and run data reside?
   - Cloud-hosted is acceptable → **SaaS**
   - Must stay in your infrastructure → **Hybrid**
   - Must be completely isolated/air-gapped → **Air-gapped**

2. **Infrastructure Complexity**: How much infrastructure control do you want?
   - Minimal → **SaaS**
   - Moderate → **Hybrid**
   - Full control → **Air-gapped**

3. **Time to Value**: How quickly do you need to be productive?
   - Within 1 hour → **SaaS**
   - Within 4 hours → **Hybrid**
   - Within 8 hours (or longer planning period) → **Air-gapped**

4. **Compliance Requirements**: What regulations apply to your organization?
   - General business → **SaaS**
   - Data residency rules → **Hybrid**
   - Strict isolation requirements → **Air-gapped**

## Security & Compliance

All ZenML Pro deployments include:

- ✅ **SOC 2 Type II** certification
- ✅ **ISO 27001** certification
- ✅ **Vulnerability Assessment Reports** available on request
- ✅ **Software Bill of Materials (SBOM)** available on request

For software deployed on your infrastructure (Hybrid and Air-gapped scenarios), ZenML provides comprehensive security documentation to support your compliance requirements.

## Running Pipelines from the Dashboard

All deployment scenarios support running pipeline snapshots from the dashboard through [workload managers](workload-managers.md). Workload managers are built into the ZenML Pro server and can be configured to orchestrate pipeline execution on your Kubernetes cluster, AWS ECS, or GCP infrastructure.

Learn more: [Understanding Workload Managers](workload-managers.md)

## Next Steps

- **Ready to start?** [Choose SaaS Deployment](saas-deployment.md)
- **Need metadata control?** [Set up Hybrid Deployment](hybrid-deployment.md)
- **Require complete isolation?** [Configure Air-gapped Deployment](air-gapped-deployment.md)
- **Deploying on your own infrastructure?** [See Self-hosted Deployment Guide](self-hosted.md)
- **Want to run pipelines from the dashboard?** [Configure Workload Managers](workload-managers.md)

{% hint style="info" %}
Not sure which option is right for you? [Book a call](https://www.zenml.io/book-your-demo) with our team to discuss your specific requirements.
{% endhint %}
