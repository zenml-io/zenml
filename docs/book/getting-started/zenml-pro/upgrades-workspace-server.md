---
description: How to upgrade ZenML Workspace Servers.
icon: database
---

# Upgrading the Workspace Server

This page covers upgrade procedures for ZenML Workspace Servers across different deployment scenarios.

{% hint style="warning" %}
Always upgrade the Control Plane first, then upgrade Workspace Servers. This ensures compatibility and prevents potential issues.
{% endhint %}

## SaaS Deployments

For SaaS deployments, workspace servers can be upgraded in a self-service manner directly through the ZenML frontend.

## Hybrid or self-hosted Deployments

In hybrid or self-hosted deployments, you manage the Control Plane yourself.

**Tip:** Always review the [release notes](https://docs.zenml.io/changelog/server-sdk) for workspace server updates before upgrading. For any issues or questions, contact ZenML Support.

**Upgrade Process:**

1. Navigate to workspace settings in the ZenML Pro UI
2. Initiate the workspace upgrade
3. The system automatically performs a database backup to ensure rollback is possible
4. Monitor the upgrade progress in the UI

This provides a safe and reliable process to keep your workspaces up to date with minimal operational overhead.

## Hybrid Deployments

To upgrade workspace servers in a hybrid deployment:

1. **Update Helm Values:**  
   Change the Workspace Server version in your `values.yaml` file to reference the new image tag (the version you want to upgrade to).

2. **Apply the Upgrade:**  
   Re-apply the Helm chart to perform the upgrade:
   ```bash
   helm upgrade <your-workspace-release-name> zenml/zenml \
     --namespace <your-workspace-namespace> \
     --values values.yaml
   ```

3. **Automatic Backup:**  
   As part of the upgrade process, the system takes a database backup automatically before proceeding. This ensures you can safely roll back if anything goes wrong.

4. **Monitor the Upgrade:**  
   Watch the logs and pod statuses to verify a healthy rollout:
   ```bash
   kubectl -n <your-workspace-namespace> get pods
   kubectl -n <your-workspace-namespace> logs <workspace-server-pod>
   ```

5. **Rollback on Failure:**  
   If the upgrade fails for any reason, the system will automatically roll back to the previous workspace server version using the backup. No manual intervention is required.

6. **Zero Downtime:**  
   Workspace upgrades are orchestrated to be highly available—users should not experience downtime during the upgrade process.

{% hint style="info" %}
**Workload Manager Updates:** When upgrading, check the [release notes](https://docs.zenml.io/changelog/server-sdk) for any changes to workload manager configuration. If you have configured a workload manager, you may need to update environment variables in your Helm values. See [Workspace Server Configuration](deploy-workspace-snapshots.md) for the full configuration reference.
{% endhint %}

## Rollback Procedures

If the upgrade fails or causes issues:

1. **Helm rollback:**
   ```bash
   helm rollback zenml <previous-revision> --namespace zenml-workspace
   ```

2. **Restore database** if needed from the backup taken before the upgrade.

3. **Verify rollback:**
   ```bash
   kubectl -n zenml-workspace get pods
   ```

## Related Documentation

- [Upgrades and Updates](upgrades-updates.md) - Overview of upgrade procedures
- [Upgrading Control Plane](upgrades-control-plane.md) - Control Plane upgrade procedures
- [Workspace Server Deployment](deploy-workspace-k8s.md) - Configuration reference

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>

