---
description: >-
  Learn about ZenML Pro Self-hosted deployment - complete control and data
  sovereignty for the strictest security requirements.
icon: shield-halved
---

# Self-hosted Deployment

ZenML Pro Self-hosted deployment provides complete control and data sovereignty for organizations with the strictest security, compliance, or regulatory requirements. All ZenML components run entirely within your infrastructure with no external dependencies or internet connectivity required.

{% hint style="info" %}
To learn more about Self-hosted deployment, [book a call](https://www.zenml.io/book-your-demo).
{% endhint %}

## Overview

In a Self-hosted deployment, every component of ZenML Pro runs within your isolated network environment. This architecture is designed for organizations that must operate in completely disconnected environments or have regulatory requirements preventing any external communication.

![ZenML Pro self-hosted deployment architecture](.gitbook/assets/cloud_architecture_scenario_2.png)

## Architecture

### What Runs Where

| Component | Location | Purpose |
|-----------|----------|---------|
| Pro Control Plane | Your Infrastructure | Manages authentication, RBAC, and workspace coordination |
| ZenML Pro Server(s) | Your Infrastructure | Handles pipeline orchestration and execution |
| Pro Metadata Store | Your Infrastructure | Stores user management, RBAC, and organizational data |
| Workspace Metadata Store | Your Infrastructure | Stores pipeline runs, model metadata, and tracking information |
| Secrets Store | Your Infrastructure | Stores all credentials and sensitive configuration |
| Identity Provider | Your Infrastructure | Handles authentication (OIDC/LDAP/SAML) |
| Pro Dashboard | Your Infrastructure | Web interface for all ZenML Pro features |
| Compute Resources | Your infrastructure through [stacks](https://docs.zenml.io/stacks) | Executes pipeline steps and training jobs |
| Data & Artifacts | Your infrastructure through [stacks](https://docs.zenml.io/stacks) | Stores datasets, models, and pipeline artifacts |

{% hint style="success" %}
Zero data leaves your environment. All components, metadata, and ML artifacts remain within your infrastructure boundaries.
{% endhint %}

### Complete Isolation

Users authenticate via local password protected accounts or through your internal identity provider (LDAP/AD/OIDC), and the control plane running in your infrastructure handles both authentication and RBAC. All communication happens entirely within your infrastructure boundary with zero external dependencies or internet connectivity required.

## Key Benefits

### Maximum Security & Control

Self-hosted deployment operates with complete air-gap capability, requiring no internet connectivity for operation. All components are self-contained with zero external dependencies. You have full control over all security configurations, the system operates entirely within your security perimeter, and all logging and monitoring stays within your infrastructure for audit compliance.

### Regulatory Compliance

All data stays within your jurisdiction, meeting data residency requirements. The deployment is suitable for controlled data environments requiring ITAR/EAR compliance, healthcare and privacy regulations like HIPAA and GDPR, government and defense classified environments, and banking and financial regulations.

### Enterprise Control

You can integrate with your existing identity provider (LDAP/AD/OIDC) and deploy on any infrastructure including cloud, on-premises, or edge. You control update schedules and versions, implement your own backup and disaster recovery policies, and have full control over resource allocation and costs.

## Ideal Use Cases

Self-hosted deployment is essential for government and defense organizations with classified data requirements, regulated industries (healthcare, finance) with strict data residency requirements, and organizations in restricted regions with limited or no internet connectivity. It's also the right choice for research institutions handling sensitive or proprietary research data, critical infrastructure operators requiring isolated systems, companies with ITAR/EAR compliance requirements, enterprises with zero-trust policies prohibiting external communication, and organizations requiring full control over all aspects of their MLOps platform.

## Deployment Options

### On-Premises Data Center

Deploy on your own hardware with physical servers or private cloud infrastructure. This option provides complete infrastructure control, integration with existing systems, and support for custom hardware configurations.

### Private Cloud (AWS, Azure, GCP)

Deploy in an isolated cloud VPC with no internet gateway and private networking only. You can use cloud-native services while leveraging cloud scalability within your security boundary.

### Hybrid Multi-Cloud

Deploy across multiple environments combining on-premises infrastructure with private cloud, multi-region setups for disaster recovery, or edge plus datacenter hybrid configurations. This option maintains complete isolation across all environments.

## Operations & Maintenance

### Updates & Upgrades

ZenML provides new versions as offline bundles. The update process involves receiving the new bundle (typically by pulling Docker images via your approved transfer method), carefully reviewing the release notes and migration instructions to understand all changes and requirements, testing in a staging environment first, backing up your current database and configuration state, applying updates using Helm upgrade commands or your Infrastructure-as-Code tools, verifying functionality with health checks and tests, and monitoring for any issues post-upgrade.

### Disaster Recovery

Your disaster recovery plan should include MySQL streaming replication to a backup site, artifact store synchronization to a DR location, version-controlled infrastructure as code for configuration backup, documented DR runbooks, and regular quarterly testing of DR procedures.

## Security Hardening

### Network Security

Isolate ZenML components in dedicated network segments, restrict traffic to only required ports with firewall rules, encrypt all communication with TLS, and use an internal CA for certificate issuance.

### Access Control

Apply the principle of least privilege by granting minimal required permissions. Use dedicated service accounts for automation and log all authentication and authorization events for audit purposes.

### Container Security

Scan all container images before deployment, monitor container behavior at runtime, enforce security standards with pod security policies, and configure resource limits to prevent resource exhaustion attacks.

## Support & Documentation

### What ZenML Provides

ZenML provides complete offline installation bundles, comprehensive setup and operation guides, a full software bill of materials (SBOM) for compliance, security assessment documentation with vulnerability reports, pre-deployment planning support through architecture consultation, guidance during initial setup, and new versions as offline bundles.

### What You Manage

You are responsible for infrastructure (hardware, networking, storage), day-to-day operations (monitoring, backups, user management), security policies (firewall rules, access controls), compliance (audit logs, security assessments), and applying new versions using the provided bundles.

### Support Model

Contact [cloud@zenml.io](mailto:cloud@zenml.io) for pre-sales architecture consultation, deployment planning and sizing, security documentation requests, offline support packages, and update and upgrade assistance.

## Licensing

Air-gapped deployments are provided under commercial software license agreements, with license fees and terms defined on a per-customer basis. Each contract includes detailed license terms and conditions appropriate to the deployment.

## Security Documentation

The following documentation is available on request for compliance and security reviews: vulnerability assessment reports with full security analysis, software bill of materials (SBOM) with complete dependency list, architecture security review with threat model and mitigations, compliance mappings for NIST, CIS, GDPR, and HIPAA, and a security hardening guide with best practices for your deployment.

## Comparison with Other Deployments

| Feature | SaaS | Hybrid SaaS | Self-hosted |
|---------|------|-------------|-------------|
| Internet Required | Yes (metadata) | Yes (control plane) | No |
| Setup Time | Minutes | Hours/Days | Days/Weeks |
| Maintenance | Zero | Partial | Full control |
| Data Location | Mixed | Your infra | 100% yours |
| User Management | ZenML | ZenML | Your IDP |
| Update Control | Automatic | Automatic CP | You decide |
| Customization | Limited | Moderate | Complete |
| Best For | Fast start | Balance | Max security |

[Compare all deployment options →](scenarios.md)

## Migration Path

### From ZenML OSS to Self-hosted Pro

If you're interested in migrating from ZenML OSS to a Self-hosted Pro deployment, we're here to help guide you through every step of the process. Migration paths are highly dependent on your specific environment, infrastructure setup, and current ZenML OSS deployment configuration. It's possible to migrate existing stacks or even existing metadata from existing OSS deployments—we can figure out how and what to migrate together in a call. [Book a migration consultation](https://www.zenml.io/book-your-demo) or email us at [cloud@zenml.io](mailto:cloud@zenml.io). Your ZenML representative will work with you to assess your current setup, understand your Self-hosted requirements, and provide a tailored migration plan that fits your environment.

### From Other Pro Deployments

If you're moving from SaaS or Hybrid to Self-hosted, migration paths can vary significantly depending on your organization's size, data residency requirements, and current ZenML setup. We recommend discussing your plans with a ZenML solutions architect. [Book a migration consultation](https://www.zenml.io/book-your-demo) or email us at [cloud@zenml.io](mailto:cloud@zenml.io). Your ZenML representative will provide you with a tailored migration checklist, technical documentation, and direct support to ensure a smooth transition with minimal downtime.


## Related Resources

- [System Architecture](system-architecture.md)
- [Scenarios](scenarios.md)
- [SaaS Deployment](saas-deployment.md)
- [Hybrid SaaS Deployment](hybrid-deployment.md)
- [Configuration Details](configuration-details.md)
- [Upgrades and Updates](upgrades-updates.md)

## Get Started

Ready to deploy ZenML Pro in a Self-hosted environment? [Book a Demo](https://www.zenml.io/book-your-demo) or [contact us](mailto:cloud@zenml.io) for detailed deployment planning.
