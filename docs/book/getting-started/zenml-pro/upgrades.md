---
description: How to upgrade ZenML Pro components - Control Plane and Workspace Servers.
icon: arrow-up-right-dots
---

# Upgrades & Updates

This guide covers upgrading ZenML Pro components for all deployment types.

{% hint style="warning" %}
Always upgrade the Control Plane first, then upgrade Workspace Servers. This ensures compatibility and prevents potential issues.
{% endhint %}

## Before You Upgrade

### Check Release Notes

- For ZenML Pro Control Plane: Check available versions in the [ZenML Pro ArtifactHub repository](https://artifacthub.io/packages/helm/zenml-pro/zenml-pro)
- For ZenML Pro Workspace Servers: Check available versions in the [ZenML OSS ArtifactHub repository](https://artifacthub.io/packages/helm/zenml/zenml) and review the [ZenML GitHub releases page](https://github.com/zenml-io/zenml/releases) for release notes and breaking changes

### Backup Checklist

Before any upgrade:

1. **Database backup** - Export your database
2. **Values.yaml files** - Save copies of your Helm values
3. **TLS certificates** - Ensure certificates are backed up

### Version Compatibility

### Database Migrations

Some updates may require database migrations:

1. **Review migration guide** in release notes
2. **Monitor logs** for any migration-related errors
3. **Verify data integrity** after upgrade
4. **Test key features** (workspace access, pipeline runs, etc.)

## Upgrading the Control Plane

### SaaS Deployments

#### Workspace Upgrades

For SaaS deployments, workspace servers can be upgraded in a self-service manner directly through the ZenML frontend. When a user initiates a workspace upgrade, the system automatically performs a database backup to ensure rollback is possible in the unlikely event of issues. This provides a safe and reliable process to keep your workspaces up to date with minimal operational overhead.

#### Control Plane Upgrades

The ZenML SaaS Control Plane is periodically upgraded by the ZenML team. When an upgrade is planned, any changes to the minimum compatible workspace server version are communicated to all affected users ahead of time. This gives organizations ample time to perform required workspace server upgrades and maintain a compatible environment across their infrastructure.


### Hybrid Deployments

#### Workspace Upgrades

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

**Tip:** Always review the [release notes](https://docs.zenml.io/changelog) for workspace server updates before upgrading. For any issues or questions, contact ZenML Support.


#### Control Plane Upgrades

The ZenML SaaS Control Plane is periodically upgraded by the ZenML team. When an upgrade is planned, any changes to the minimum compatible workspace server version are communicated to all affected users ahead of time. This gives organizations ample time to perform required workspace server upgrades and maintain a compatible environment across their infrastructure.

### Self-hosted Deployments

In self-hosted deployments, you manage both the Control Plane and Workspace Servers. Always upgrade the Control Plane first, then upgrade Workspace Servers.

#### Preparing Artifacts (Air-gapped)

For air-gapped environments:

1. Request offline bundle from ZenML Support containing:
   - Updated container images
   - Updated Helm charts
   - Release notes and migration guide
   - Vulnerability assessment (if applicable)
2. If using a private registry, copy the new container images to your private registry
3. Transfer bundle to your air-gapped environment using approved methods
4. Extract and load new images, tag and push to your internal registry

#### Control Plane Upgrades

To upgrade the Control Plane in a self-hosted deployment:

1. **Update Helm Values:**  
   Change the Control Plane version in your `values.yaml` file to reference the new image tag.

2. **Apply the Upgrade:**  
   
   **Option A - In-place upgrade with existing values** (if no config changes needed):
   ```bash
   helm upgrade zenml-pro ./zenml-pro-<new-version>.tgz \
     --namespace zenml-pro \
     --reuse-values
   ```

   **Option B - Retrieve, modify and reapply values** (if config changes needed):
   ```bash
   # Get the current values
   helm --namespace zenml-pro get values zenml-pro > current-values.yaml

   # Edit current-values.yaml if needed, then upgrade
   helm upgrade zenml-pro ./zenml-pro-<new-version>.tgz \
     --namespace zenml-pro \
     --values current-values.yaml
   ```

3. **Monitor the Upgrade:**  
   Watch the logs and pod statuses to verify a healthy rollout:
   ```bash
   kubectl -n zenml-pro get pods
   kubectl -n zenml-pro logs <control-plane-pod>
   ```

4. **Verify the Upgrade:**
   - Check pod status
   - Review logs
   - Test connectivity
   - Access the dashboard

**Tip:** Always review the [release notes](https://docs.zenml.io/changelog) before upgrading. For any issues or questions, contact ZenML Support.

#### Workspace Upgrades

To upgrade Workspace Servers in a self-hosted deployment:

1. **Update Helm Values:**  
   Change the Workspace Server version in your `values.yaml` file to reference the new image tag.

2. **Apply the Upgrade:**  
   
   For each workspace, perform either:

   **Option A - In-place upgrade with existing values**:
   ```bash
   helm upgrade zenml ./zenml-<new-version>.tgz \
     --namespace zenml-workspace \
     --reuse-values
   ```

   **Option B - Retrieve, modify and reapply values**:
   ```bash
   # Get the current values
   helm --namespace zenml-workspace get values zenml > current-workspace-values.yaml

   # Edit current-workspace-values.yaml if needed, then upgrade
   helm upgrade zenml ./zenml-<new-version>.tgz \
     --namespace zenml-workspace \
     --values current-workspace-values.yaml
   ```

3. **Monitor the Upgrade:**  
   Watch the logs and pod statuses to verify a healthy rollout:
   ```bash
   kubectl -n zenml-workspace get pods
   kubectl -n zenml-workspace logs <workspace-server-pod>
   ```

4. **Verify the Upgrade:**
   - Check all pods are running
   - Review logs
   - Run health checks
   - Test dashboard access

**Tip:** Always review the [release notes](https://docs.zenml.io/changelog) for workspace server updates before upgrading. For any issues or questions, contact ZenML Support.

## Post-Upgrade Verification

### Health Checks

### Testing Connectivity

### Validating Functionality

## Rollback Procedures

### Rolling Back the Control Plane

### Rolling Back Workspace Servers

## Troubleshooting Upgrades

### Common Issues

### Getting Help

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
