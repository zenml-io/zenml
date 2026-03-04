---
description: Compare ZenML Pro deployment scenarios to find the right fit for your organization.
icon: code-merge
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Scenarios

ZenML Pro offers three flexible deployment options to match your organization's security, compliance, and operational needs. This page helps you understand the differences and choose the right scenario for your use case.

<!-- DIAGRAM: Visual comparison showing SaaS, Hybrid, and Self-hosted - what runs where (ZenML vs Your Infrastructure) -->

## Quick Comparison

| Entity | SaaS | Hybrid SaaS | Self-hosted |
|-------------------|------|-------------|-------------|
| **ZenML Workspace Server** | ZenML infrastructure | Your infrastructure | Your infrastructure |
| **ZenML Control Plane** | ZenML infrastructure | ZenML infrastructure | Your infrastructure |
| **ZenML Pro UI** | ZenML infrastructure | ZenML infrastructure | Your infrastructure |
| **Stack (Pipeline Compute & Data)** | Your infrastructure | Your infrastructure | Your infrastructure |
| **Setup Time** | ⚡ ~1 hour | ~4 hours | ~8 hours |
| **Maintenance Responsibility** | Fully managed | Partially managed (workspace maintenance required) | Fully customer managed |
| **Best For** | Teams wanting minimal infrastructure overhead and fastest time-to-value | Organizations with security/compliance requirements but wanting simplified user management | Organizations requiring complete data isolation and on-premises control |

{% hint style="info" %}
In all of these cases the client SDK that you pip install into your development environment is the same one found here: https://pypi.org/project/zenml/
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

[Set up SaaS deployment →](saas-deployment.md)

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

[Set up Hybrid deployment →](hybrid-deployment.md)

### Self-hosted Deployment

Choose **Self-hosted** if you need complete control with no external dependencies.

**What runs where:**
- All components: Your infrastructure (completely isolated)

**Key Benefits:**
- 🔒 Complete data sovereignty
- 🚫 No external network dependencies
- 🛡️ Maximum security posture

**Ideal for:** Regulated industries (healthcare, finance, defense), government organizations, enterprises with strict data residency requirements, environments requiring offline operation.

[Set up Self-hosted deployment →](self-hosted-deployment.md)

## Making Your Choice

Consider these factors when deciding:

1. **Metadata Storage Requirements**: Where must your ML metadata and run data reside?
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
   - Hours to Days (depending on your complexity) → **Self-hosted**

4. **Compliance Requirements**: What regulations apply to your organization?
   - General business → **SaaS**
   - Data residency rules → **Hybrid**
   - Strict isolation requirements → **Self-hosted**

{% hint style="info" %}
Not sure which option is right for you? [Book a call](https://www.zenml.io/book-your-demo) with our team to discuss your specific requirements.
{% endhint %}

## Next Steps

- **Ready to start?** [Choose SaaS Deployment](saas-deployment.md)
- **Need metadata control?** [Set up Hybrid Deployment](hybrid-deployment.md)
- **Require complete isolation?** [Configure Self-hosted Deployment](self-hosted-deployment.md)

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>

