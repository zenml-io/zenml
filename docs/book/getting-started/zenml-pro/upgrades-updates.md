---
description: How to upgrade ZenML Pro components.
icon: arrow-up-right-dots
---

# Upgrades and Updates

This section covers upgrading ZenML Pro components for all deployment types. Each component has its own upgrade procedures and considerations.

{% hint style="warning" %}
Always upgrade the Control Plane first, then upgrade Workspace Servers. This ensures compatibility and prevents potential issues.
{% endhint %}

<table data-view="cards"><thead><tr><th></th><th></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td><strong>Control Plane</strong></td><td>Upgrade procedures for the Control Plane across SaaS, Hybrid, and Self-hosted deployments.</td><td><a href="upgrades-control-plane.md">upgrades-control-plane.md</a></td></tr><tr><td><strong>Workspace Server</strong></td><td>Upgrade procedures for Workspace Servers across all deployment scenarios.</td><td><a href="upgrades-workspace-server.md">upgrades-workspace-server.md</a></td></tr><tr><td><strong>Workload Manager</strong></td><td>Upgrade procedures for Workload Managers and runner images.</td><td><a href="upgrades-workload-manager.md">upgrades-workload-manager.md</a></td></tr></tbody></table>

## Before You Upgrade

### Check Release Notes

- For ZenML Pro Control Plane: Check available versions in the [ZenML Pro ArtifactHub repository](https://artifacthub.io/packages/helm/zenml-pro/zenml-pro)
- For ZenML Pro Workspace Servers: Check available versions in the [ZenML OSS ArtifactHub repository](https://artifacthub.io/packages/helm/zenml/zenml) and review the [ZenML GitHub releases page](https://github.com/zenml-io/zenml/releases) for release notes and breaking changes

### Backup Checklist

Before any upgrade:

1. **Database backup** - Export your database
2. **Values.yaml files** - Save copies of your Helm values
3. **TLS certificates** - Ensure certificates are backed up

### Database Migrations

Some updates may require database migrations:

1. **Review migration related changes** in release notes
2. **Monitor logs** for any migration-related errors
3. **Verify data integrity** after upgrade
4. **Test key features** (workspace access, pipeline runs, etc.)

## Post-Upgrade Verification

After upgrading any component:

1. **Health Checks** - Verify all pods are running
2. **Test Connectivity** - Confirm SDK can connect
3. **Validate Functionality** - Test pipeline execution
4. **Review Logs** - Check for errors or warnings

## Related Documentation

- [Configuration Details](configuration-details.md) - Component configuration reference
- [System Architecture](system-architecture.md) - Understand component interactions
- [Scenarios](scenarios.md) - Deployment scenarios and guides

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>

