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

| Component                    | Location                                                           | Purpose                                                        |
| ---------------------------- | ------------------------------------------------------------------ | -------------------------------------------------------------- |
| **Pro Control Plane**        | Your Infrastructure                                                | Manages authentication, RBAC, and workspace coordination       |
| **ZenML Pro Server(s)**      | Your Infrastructure                                                | Handles pipeline orchestration and execution                   |
| **Pro Metadata Store**       | Your Infrastructure                                                | Stores user management, RBAC, and organizational data          |
| **Workspace Metadata Store** | Your Infrastructure                                                | Stores pipeline runs, model metadata, and tracking information |
| **Secrets Store**            | Your Infrastructure                                                | Stores all credentials and sensitive configuration             |
| **Identity Provider**        | Your Infrastructure                                                | Handles authentication (OIDC/LDAP/SAML)                        |
| **Pro Dashboard**            | Your Infrastructure                                                | Web interface for all ZenML Pro features                       |
| **Compute Resources**        | Your infrastructure through [stacks](https://docs.zenml.io/stacks) | Executes pipeline steps and training jobs                      |
| **Data & Artifacts**         | Your infrastructure through [stacks](https://docs.zenml.io/stacks) | Stores datasets, models, and pipeline artifacts                |

### Complete Isolation

{% hint style="success" %}
**Complete data sovereignty**: Zero data leaves your environment. All components, metadata, and ML artifacts remain within your infrastructure boundaries.
{% endhint %}


In Self-hosted deployment, users authenticate via your internal identity provider (LDAP/AD/OIDC), and the control plane (running in your infrastructure) handles both authentication and RBAC. All communication happens entirely within your infrastructure boundary with zero external dependencies or internet connectivity required.

## Key Benefits

### Maximum Security & Control

* Complete air-gap - No internet connectivity required for operation
* Zero external dependencies - All components self-contained
* Custom security policies - Full control over all security configurations
* Network isolation - Operates within your security perimeter
* Audit compliance - Complete logging and monitoring within your infrastructure

### Regulatory Compliance

* Data residency - All data stays within your jurisdiction
* ITAR/EAR compliance - Suitable for controlled data environments
* HIPAA/GDPR ready - Meet healthcare and privacy regulations
* Government/Defense - Suitable for classified environments
* Financial services - Meet banking and financial regulations

### Enterprise Control

* Custom identity provider - Integrate with your LDAP/AD/OIDC
* Infrastructure flexibility - Deploy on any infrastructure (cloud, on-prem, edge)
* Version control - Control update schedules and versions
* Backup strategy - Implement your own backup and DR policies
* Resource optimization - Full control over resource allocation and costs

## Ideal Use Cases

Self-hosted deployment is essential for:

* **Government and defense** organizations with classified data requirements
* **Regulated industries** (healthcare, finance) with strict data residency requirements
* **Organizations in restricted regions** with limited or no internet connectivity
* **Research institutions** handling sensitive or proprietary research data
* **Critical infrastructure** operators requiring isolated systems
* **Companies with ITAR/EAR compliance** requirements
* **Enterprises with zero-trust policies** prohibiting external communication
* **Organizations requiring full control** over all aspects of their MLOps platform

## Deployment Options

### On-Premises Data Center

Deploy on your own hardware:

* Physical servers or private cloud
* Complete infrastructure control
* Integration with existing systems
* Custom hardware configurations

### Private Cloud (AWS, Azure, GCP)

Deploy in isolated cloud VPC:

* No internet gateway
* Private networking only
* Use cloud-native services
* Leverage cloud scalability within your boundary

### Hybrid Multi-Cloud

Deploy across multiple environments:

* On-premises + private cloud
* Multi-region for DR
* Edge + datacenter hybrid
* Maintain complete isolation across all environments


## Deployment Architecture

![Complete ZenML Services diagram on top of Kubernetes](.gitbook/assets/full_zenml_infra.png)

The diagram above illustrates a complete Self-hosted ZenML Pro deployment with all components running within your organization's VPC. This architecture ensures zero external communication while providing full enterprise MLOps capabilities.

### Architecture Components

#### Client Access

* Browser Tab - Access the ZenML UI dashboard
* Developer Laptop / CI - Connect to workspaces 

#### Kubernetes Cluster (Compute and Services Layer)

**zenml-controlplane-namespace**

* UI Pod - Hosts the ZenML Pro dashboard, connects to control plane and all workspaces
* Control Plane Pod - API Server and User Management / RBAC

**zenml-workspace-namespace**

* Workspace Server Pod - ZenML Server with API Server and Workload Manager
* Manages pipelines, stacks, snapshots, etc...

**zenml-runners-namespace**

* Runner Pods - Created on-demand for snapshots 

**orchestrator-namespace**

* Orchestrator Pods - Pipeline execution environment in case of Kubernetes orchestrator

#### Data and Storage Layer

* MySQL Database - Stores workspace and control plane metadata (TCP 3306)
* Secrets Backend - AWS Secrets Manager or Vault (optional)
* Artifact Store - S3, GCS, or Azure Blob for models, datasets, and artifacts
* Container Registry - AWS ECR, Google Artifact Registry, or Azure for pipeline images


## Pre-requisites

Before deployment, ensure you have:

#### Infrastructure Requirements

* Kubernetes cluster (recommended) or VM infrastructure
* PostgreSQL database(s) for metadata storage
* Object storage or NFS for artifacts
* Load balancer for HA configurations
* Identity provider (LDAP/AD/OIDC)

#### Network Requirements

* Internal DNS resolution
* SSL/TLS certificates (internal CA)
* Network connectivity between components
* Firewall rules for inter-component communication

#### Resource Requirements

```yaml
# Minimum requirements
Control Plane:
  CPU: xx cores
  Memory: xxGB RAM
  Storage: xxxGB

Per Workspace:
  CPU: xx cores
  Memory: xxGB RAM
  Storage: xxGB + metadata

Database:
  CPU: xx cores
  Memory: xxGB RAM
  Storage: xxxGB (scalable)
```

## Operations & Maintenance

### Updates & Upgrades

ZenML provides new versions as offline bundles:

1. **Receive new bundle**: Typically by pulling our Docker images via your approved transfer method
2. **Review release notes and compatibility notes**: Carefully review the release notes and any migration instructions included in the offline bundle to understand all changes, requirements, and potential impacts. Assess required infrastructure or configuration updates and note any changes in CI/CD actions or deployment processes before proceeding.
3. **Test in staging**: Deploy to test environment first
4. **Backup current state**: Database and configuration backups
5. **Apply updates**: Using Helm upgrade commands, or update your deployment using Terraform or other Infrastructure-as-Code (IaC) tools.
6. **Verify functionality**: Run health checks and tests
7. **Monitor**: Watch for any issues post-upgrade

### Disaster Recovery

Plan for disaster scenarios:

1. **Database replication**: PostgreSQL streaming replication to backup site
2. **Artifact replication**: Sync artifact stores to DR location
3. **Configuration backup**: Version-controlled infrastructure as code
4. **Runbook**: Document DR procedures
5. **Regular testing**: Test DR procedures quarterly

## Security Hardening

### Network Security

* **Network segmentation**: Isolate ZenML components in dedicated network segments
* **Firewall rules**: Restrict traffic to only required ports
* **TLS everywhere**: Encrypt all communication
* **Certificate management**: Use internal CA for certificate issuance

### Access Control

* **Principle of least privilege**: Grant minimal required permissions
* **Service accounts**: Use dedicated service accounts for automation
* **Audit logging**: Log all authentication and authorization events

### Container Security

* **Image scanning**: Scan all container images before deployment
* **Runtime security**: Monitor container behavior
* **Pod security policies**: Enforce security standards
* **Resource limits**: Prevent resource exhaustion attacks

## Support & Documentation

### What ZenML Provides

* **Deployment packages**: Complete offline installation bundles
* **Documentation**: Comprehensive setup and operation guides
* **SBOM**: Full software bill of materials for compliance
* **Vulnerability reports**: Security assessment documentation
* **Architecture consultation**: Pre-deployment planning support
* **Deployment assistance**: Guidance during initial setup
* **Update packages**: New versions as offline bundles

### What You Manage

* **Infrastructure**: Hardware, networking, storage
* **Day-to-day operations**: Monitoring, backups, user management
* **Security policies**: Firewall rules, access controls
* **Compliance**: Audit logs, security assessments
* **Updates**: Applying new versions using provided bundles

### Support Model

Contact [cloud@zenml.io](mailto:cloud@zenml.io) for:

* Pre-sales architecture consultation
* Deployment planning and sizing
* Security documentation requests
* Offline support packages
* Update and upgrade assistance

## Licensing

Air-gapped deployments are provided under commercial software license agreements, with license fees and terms defined on a per-customer basis. Each contract includes detailed license terms and conditions appropriate to the deployment.

## Security Documentation

Available on request for compliance and security reviews:

* ✅ **Vulnerability Assessment Reports**: Full security analysis
* ✅ **Software Bill of Materials (SBOM)**: Complete dependency list
* ✅ **Architecture security review**: Threat model and mitigations
* ✅ **Compliance mappings**: NIST, CIS, GDPR, HIPAA guidance
* ✅ **Security hardening guide**: Best practices for your deployment

## Comparison with Other Deployments

| Feature           | SaaS           | Hybrid SaaS         | Self-hosted      |
| ----------------- | -------------- | ------------------- | ---------------- |
| Internet Required | Yes (metadata) | Yes (control plane) | **No**           |
| Setup Time        | Minutes        | Hours/Days          | Days/Weeks       |
| Maintenance       | Zero           | Partial             | **Full control** |
| Data Location     | Mixed          | Your infra          | **100% yours**   |
| User Management   | ZenML          | ZenML               | **Your IDP**     |
| Update Control    | Automatic      | Automatic CP        | **You decide**   |
| Customization     | Limited        | Moderate            | **Complete**     |
| Best For          | Fast start     | Balance             | **Max security** |

[Compare all deployment options →](scenarios.md)

## Migration Path

### From ZenML OSS to Self-hosted Pro

If you're interested in migrating from ZenML OSS to a Self-hosted Pro deployment, we're here to help guide you through every step of the process. Migration paths are highly dependent on your specific environment, infrastructure setup, and current ZenML OSS deployment configuration.

It's possible to migrate existing stacks or even existing metadata from existing OSS deployments. We can figure out how and what to migrate together in a call.

**Next steps:**

* [Book a migration consultation →](https://www.zenml.io/book-your-demo)
* Or email us at [cloud@zenml.io](mailto:cloud@zenml.io)

Your ZenML representative will work with you to assess your current setup, understand your Self-hosted requirements, and provide a tailored migration plan that fits your environment.

### From Other Pro Deployments

If you're moving from SaaS or Hybrid to Self-hosted, migration paths can vary significantly depending on your organization's size, data residency requirements, and current ZenML setup. We recommend discussing your plans with a ZenML solutions architect.

**Next steps:**

* [Book a migration consultation →](https://www.zenml.io/book-your-demo)
* Or email us at [cloud@zenml.io](mailto:cloud@zenml.io)

Your ZenML representative will provide you with a tailored migration checklist, technical documentation, and direct support to ensure a smooth transition with minimal downtime.

## Detailed Architecture Diagram

<img src=".gitbook/assets/cloud_architecture_self_hosted_detailed (1).png" alt="ZenML Pro self-hosted deployment details" data-size="original">

## Related Resources

- [System Architecture](system-architecture.md)
- [Scenarios](scenarios.md)
- [SaaS Deployment](saas-deployment.md)
- [Hybrid SaaS Deployment](hybrid-deployment.md)
- [Configuration Details](configuration-details.md)
- [Upgrades and Updates](upgrades-updates.md)

## Get Started

Ready to deploy ZenML Pro in a Self-hosted environment?

[Book a Demo](https://www.zenml.io/book-your-demo){ .md-button .md-button--primary }

Have questions? [Contact us](mailto:cloud@zenml.io) for detailed deployment planning.
