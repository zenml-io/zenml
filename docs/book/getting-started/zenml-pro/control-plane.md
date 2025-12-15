---
description: Deep dive into the ZenML Control Plane - responsibilities, permissions, and network requirements.
icon: shield-halved
---

# Control Plane

The **ZenML Control Plane** is the organization-level management layer in ZenML Pro. It sits above individual workspaces and provides centralized authentication, authorization, and administrative functions.

## Responsibilities

The Control Plane handles organization-wide concerns that span multiple workspaces:

### Authentication & Identity

- **User authentication**: SSO integration, login flows
- **Identity federation**: SAML, OIDC, and social login providers
- **API key management**: Personal access tokens and service account credentials 

### Authorization & RBAC

- **Role management**: Define and assign org level roles (Admin, Editor, Viewer, etc.)
- **Permission enforcement**: Control who can access what across workspaces
- **Team management**: Group users into teams with shared permissions

### Organization Management

- **Workspace provisioning**: Create, configure, and delete workspaces
- **User management**: Invite users, manage memberships, handle offboarding


### Workspace Coordination

- **Workspace registry**: Maintains list of all workspaces in the organization
- **Health monitoring**: Tracks workspace status (Hybrid/Self-hosted)
- **Version management**: Coordinates workspace upgrades (SaaS only)

## Where It Runs

| Deployment | Control Plane Location |
|------------|------------------------|
| **SaaS** | ZenML infrastructure (fully managed) |
| **Hybrid** | ZenML infrastructure (fully managed) |
| **Self-hosted** | Your infrastructure (you manage) |

## Required Permissions

### For Self-hosted Deployments

When running your own Control Plane, you need:

**Database permissions:**
- Same as Workspace Server (full CRUD on control plane database)
- Separate database recommended for isolation

**Identity provider integration:**
- OAuth2/OIDC client credentials

## Network Requirements

### Ingress

The Control Plane must accept connections from:

| Source | Protocol | Purpose |
|--------|----------|---------|
| User browsers | HTTPS | Dashboard login, UI access |
| ZenML SDK clients | HTTPS | Authentication, token exchange |
| ZenML Workspace | HTTPS | Workspace registration, heartbeats |
| Identity providers | HTTPS | SSO callbacks |

### Egress

The Control Plane needs to reach:

| Destination | Protocol | Purpose |
|-------------|----------|---------|
| Identity providers | HTTPS | SSO authentication flows |
| Database | TCP | Persistent storage |

### Network Diagram

```
                     ┌─────────────────────────────────────┐
                     │         Control Plane               │
                     │      (cloud.zenml.io or yours)      │
                     └──────────────┬──────────────────────┘
                                    │
           ┌────────────────────────┼────────────────────────┐
           │                        │                        │
           ▼                        ▼                        ▼
   ┌───────────────┐       ┌───────────────┐       ┌───────────────┐
   │  Workspace A  │       │  Workspace B  │       │  Workspace C  │
   │  (Your Infra) │       │  (Your Infra) │       │  (Your Infra) │
   └───────────────┘       └───────────────┘       └───────────────┘
```

## Authentication Flows

### User Login (Browser)

```
User Browser → Control Plane → Identity Provider → Control Plane → UI
                    │
                    └── Issues session token
```

### SDK Authentication

```
SDK → Control Plane → Validates credentials → Returns API token
         │
         └── Token used for Workspace Server requests
```

### Workspace Registration (Hybrid)

```
Workspace Server → Control Plane → Validates enrollment key → Registers workspace

```

### Resource Recommendations

| Deployment Size | CPU | Memory | Notes |
|-----------------|-----|--------|-------|
| Small (< 50 users) | xxx | xxx | Single instance sufficient |
| Medium (50-500 users) | xxx | xxx | Consider high-availability setup |
| Large (> 500 users) | xxx | xxx | Multi-replica with load balancing |

## Security Considerations

### Data Handled by Control Plane

| Data Type | Sensitivity | Storage |
|-----------|-------------|---------|
| User credentials | High | Managed through IDP |
| API tokens | High | Encrypted at rest |
| Organization settings | Medium | Control Plane database |
| Audit logs | Medium | Control Plane database |
| Workspace metadata | Low | Control Plane database |

{% hint style="success" %}
The Control Plane **never** has access to your ML data, artifacts, or pipeline code. It only handles authentication and organizational metadata.
{% endhint %}

## Related Documentation

- [Workspace Server](workspace-server.md) - Pipeline metadata and execution
- [Workload Managers](workload-managers.md) - Running pipelines from the UI
- [Roles & Permissions](roles.md) - Detailed RBAC configuration
- [Service Accounts](service-accounts.md) - Programmatic access setup

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>

