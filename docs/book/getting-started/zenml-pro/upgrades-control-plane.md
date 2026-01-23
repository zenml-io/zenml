---
description: How to upgrade the ZenML Control Plane.
icon: shield-halved
---

# Upgrading the Control Plane

This page covers upgrade procedures for the ZenML Control Plane across different deployment scenarios.

{% hint style="warning" %}
Always upgrade the Control Plane first, before upgrading Workspace Servers. This ensures compatibility and prevents potential issues.
{% endhint %}

## SaaS Deployments & Hybrid Deployments

The ZenML SaaS Control Plane is periodically upgraded by the ZenML team. When an upgrade is planned, any changes to the minimum compatible workspace server version are communicated to all affected users ahead of time. This gives organizations ample time to perform required workspace server upgrades and maintain a compatible environment across their infrastructure.

**No action required** - ZenML handles all Control Plane upgrades for SaaS or Hybrid deployments.

## Self-hosted Deployments

In self-hosted deployments, you manage the Control Plane yourself.

**Tip:** Always review the [release notes](https://docs.zenml.io/changelog/pro-control-plane) before upgrading. For any issues or questions, contact ZenML Support.

### Preparing updated software bundle (only in case of Air-gapped environments)

For air-gapped environments:

1. Request offline bundle from ZenML Support containing:
   - Updated container images
   - Updated Helm charts
   - Release notes and migration guide
   - Vulnerability assessment (if applicable)
2. If using a private registry, copy the new container images to your private registry
3. Transfer bundle to your air-gapped environment using approved methods
4. Extract and load new images, tag and push to your internal registry

### Upgrade Procedure

To upgrade the Control Plane in a self-hosted deployment:

1. **Update Helm Values:**  
   Change the Control Plane version in your `values.yaml` file to reference the new image tag.

2. **Apply the Upgrade:**  
   
   **Option A - In-place upgrade with existing values** (if no config changes needed):
   ```bash
   helm upgrade zenml-pro ./zenml-pro-<new-version>.tgz \
     --namespace <your-control-plane-namespace> \
     --reuse-values
   ```

   **Option B - Retrieve, modify and reapply values** (if config changes needed):
   ```bash
   # Get the current values
   helm --namespace <your-control-plane-namespace> get values zenml-pro > current-values.yaml

   # Edit current-values.yaml if needed, then upgrade
   helm upgrade zenml-pro ./zenml-pro-<new-version>.tgz \
     --namespace <your-control-plane-namespace> \
     --values current-values.yaml
   ```

3. **Monitor the Upgrade:**  
   Watch the logs and pod statuses to verify a healthy rollout:
   ```bash
   kubectl -n <your-control-plane-namespace> get pods
   kubectl -n <your-control-plane-namespace> logs <control-plane-pod>
   ```

4. **Verify the Upgrade:**
   - Check pod status
   - Review logs
   - Test connectivity
   - Access the dashboard


## Rollback Procedures

If the upgrade fails or causes issues:

1. **Helm rollback:**
   ```bash
   helm rollback zenml-pro <previous-revision> --namespace <your-control-plane-namespace>
   ```

2. **Verify rollback:**
   ```bash
   kubectl -n <your-control-plane-namespace> get pods
   ```

3. **Review logs** to understand what went wrong before attempting the upgrade again.

## Related Documentation

- [Upgrades and Updates](upgrades-updates.md) - Overview of upgrade procedures
- [Upgrading Workspace Server](upgrades-workspace-server.md) - Workspace Server upgrade procedures
- [Control Plane Deployment](deploy-control-plane-k8s.md) - Configuration reference

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>

