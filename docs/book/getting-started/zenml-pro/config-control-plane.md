---
description: Configuration reference for the ZenML Control Plane.
icon: shield-halved
---

# Control Plane Configuration

This page provides the configuration reference for the ZenML Control Plane. For an overview of what the Control Plane does, see [System Architecture](system-architecture.md#control-plane).

{% hint style="info" %}
This configuration is only relevant for **Self-hosted** deployments. In SaaS and Hybrid deployments, the Control Plane is fully managed by ZenML.
{% endhint %}

<!-- DIAGRAM: Control Plane network connectivity showing ingress from browsers/SDK/workspaces and egress to IDP/database -->

## Permissions

When running your own Control Plane, you need database permissions (full CRUD on a dedicated control plane database, separate from workspace databases) and OAuth2/OIDC client credentials for identity provider integration.

## Network Requirements

The Control Plane must accept connections from and reach the following:

| Direction | Source/Destination | Protocol | Purpose |
|-----------|-------------------|----------|---------|
| **Ingress** | User browsers | HTTPS | Dashboard login, UI access |
| **Ingress** | ZenML SDK clients | HTTPS | Authentication, token exchange |
| **Ingress** | ZenML Workspaces | HTTPS | Workspace registration, heartbeats |
| **Ingress** | Identity providers | HTTPS | SSO callbacks |
| **Egress** | Identity providers | HTTPS | SSO authentication flows |
| **Egress** | Database | TCP | Persistent storage |


## Security

The Control Plane handles sensitive authentication data but never accesses your ML data, artifacts, or pipeline code:

| Data Type | Sensitivity | Storage |
|-----------|-------------|---------|
| User credentials | High | Managed through IDP |
| API tokens | High | Encrypted at rest |
| Organization settings | Medium | Control Plane database |
| Audit logs | Medium | Control Plane database |
| Workspace metadata | Low | Control Plane database |

## Related Documentation

- [System Architecture](system-architecture.md) - How components interact
- [Workspace Server Configuration](config-workspace-server.md) - Configure the Workspace Server
- [Upgrades - Control Plane](upgrades-control-plane.md) - How to upgrade the Control Plane

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
