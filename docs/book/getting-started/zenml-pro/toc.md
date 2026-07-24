# Table of contents

* [Introduction](README.md)
* [System Architecture](system-architecture.md)

## Deployments
* [Scenarios](scenarios.md)
  * [SaaS](saas-deployment.md)
  * [Hybrid](hybrid-deployment.md)
  * [Self-hosted](self-hosted-deployment.md)
* [Deployment Details](deploy-details.md)
  * [Prerequisites](deploy-prerequisites.md)
  * Control Plane
    * [Kubernetes with Helm](deploy-control-plane-k8s.md)
  * Workspace Server
    * [Enroll Workspaces](enroll-workspace.md)
    * [Kubernetes with Helm](deploy-workspace-k8s.md)
    * [AWS ECS](deploy-workspace-ecs.md)
    * [Enable Snapshot Support](deploy-workspace-snapshots.md)
    * [Enable Event Triggers and Schedules](deploy-workspace-event-triggers-and-schedules.md)
    * [Enable Resource Pools](deploy-workspace-resource-pools.md)

## Manage

* [Single Sign-On (SSO)](sso.md)
* [User Accounts](user-accounts.md)
* [Upgrades and Updates](upgrades-updates.md)
  * [Control Plane](upgrades-control-plane.md)
  * [Workspace Server](upgrades-workspace-server.md)

## Core Concepts

* [Hierarchy](hierarchy.md)
* [Organizations](organization.md)
* [Workspaces](workspaces.md)
* [Projects](projects.md)
* [Teams](teams.md)
* [Snapshots](snapshots.md)
* [Triggers](triggers.md)
* [Resource Pools](resource-pools.md)
  * [Core Concepts](resource-pools-core-concepts.md)
  * [Admin Guide](resource-pools-admin-guide.md)
  * [User Guide](resource-pools-user-guide.md)
  * [External Workloads](resource-pools-external-workloads.md)
  * [Reconciliation Process](resource-pools-reconciliation.md)
  * [Examples](resource-pools-examples.md)

## Access Management

* [Roles & Permissions](roles.md)
* [Trusted domains](trusted-domains.md)
* [Personal Access Tokens](personal-access-tokens.md)
* [Service Accounts](service-accounts.md)
* [Secrets Stores](secrets-stores.md)
