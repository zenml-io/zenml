---
description: Deep dive into the ZenML Workspace Server - responsibilities, permissions, and network requirements.
icon: database
---

# Workspace

The **ZenML Workspace** is the central hub for your ML operations. It provides the API layer that your SDK, dashboard, and orchestrators connect to for all pipeline-related operations.

## Responsibilities

The Workspace Server handles the following core functions:

### Metadata Storage & API

- **Pipeline run tracking**: Records every pipeline execution with status, timing, and lineage
- **Step execution details**: Captures inputs, outputs, parameters, and execution metadata for each step
- **Artifact registry**: Maintains pointers to artifacts stored in your artifact store (not the artifacts themselves)
- **Model registry**: Tracks model versions, stages, and associated metadata

### Entity Management

- **Stacks and components**: Stores stack configurations and component settings
- **Pipelines and steps**: Maintains pipeline definitions and step metadata
- **Artifacts and models**: Tracks artifact versions and model lineage
- **Code repositories**: Manages connections to Git repositories

### Token & Credential Management

- **Service connector tokens**: Issues (short-lived) credentials for accessing cloud resources
- **Stack component authentication**: Provides credentials for container registries, artifact stores, orchestrators
- **API authentication**: Validates requests from SDK and dashboard

### Integration Hub

- **SDK communication**: Serves the REST API that the Python SDK connects to
- **Dashboard backend**: Provides data for the ZenML Pro UI
- **Orchestrator callbacks**: Receives status updates and metadata from running pipelines

## Where It Runs

| Deployment | Workspace Server Location |
|------------|---------------------------|
| **SaaS** | ZenML infrastructure (fully managed) |
| **Hybrid** | Your infrastructure (you manage) |
| **Self-hosted** | Your infrastructure (you manage) |

## Required Permissions

### Database Access

The Workspace Server requires a database for persistent storage:

| Database | Required Permissions |
|----------|---------------------|
| **MySQL/MariaDB** | `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `CREATE`, `ALTER`, `DROP`, `INDEX` on the ZenML database |

## Network Requirements

### Ingress

The Workspace Server must accept connections from:

| Source | Port | Protocol | Purpose |
|--------|------|----------|---------|
| ZenML SDK clients | 443 | HTTPS | API requests from client machines |
| ZenML Pro Dashboard | 443 | HTTPS | UI data requests |
| Orchestrator pods/tasks | 443 | HTTPS | Pipeline status updates, metadata logging |

### Egress

The Workspace Server needs to reach:

| Destination | Port | Protocol | Purpose |
|-------------|------|----------|---------|
| Database | 3306/5432 | TCP | MySQL/PostgreSQL |
| Control Plane | 443 | HTTPS | Authentication  |
| Secrets backend | varies | HTTPS | AWS Secrets Manager, GCP Secret Manager, etc. |
| Artifact Store | 443 | HTTPS | Artifact visualizations |

### Resource Recommendations

| Deployment Size | CPU | Memory | Storage |
|-----------------|-----|--------|---------|
| Small (< 100 runs/day) | xxx | xxx | xxx |
| Medium (100-1000 runs/day) | xxx | xxx | xxx |
| Large (> 1000 runs/day) | xxx | xxx | xxx |

## High Availability

For production deployments, consider:

- **Multiple replicas**: Run 2+ server instances behind a load balancer
- **Database replication**: Use managed database with read replicas
- **Health checks**: Configure liveness and readiness probes
- **Auto-scaling**: Scale based on CPU/memory utilization

## Related Documentation

- [Control Plane](control-plane.md) - Authentication and organization management
- [Workload Managers](workload-managers.md) - Running pipelines from the UI
- [Deployment Scenarios](deployments-overview.md) - Choose the right deployment option

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>

