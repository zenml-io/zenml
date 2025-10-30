---
description: Deploy ZenML pipeline services on Kubernetes clusters.
---

# Kubernetes Deployer

The Kubernetes deployer is a [deployer](./) flavor provided by the Kubernetes
integration. It provisions ZenML pipeline deployments as long-running services
inside a Kubernetes cluster.

{% hint style="warning" %}
This component is only meant to be used within the context of a [remote ZenML installation](https://docs.zenml.io/getting-started/deploying-zenml/). Usage with a local ZenML setup may lead to unexpected behavior!
{% endhint %}

## When to use it

Reach for the Kubernetes deployer when you need:

* you're already using Kubernetes.
* **Production-grade serving** with managed Kubernetes clusters (EKS, GKE, AKS,
  etc.) or self-hosted clusters.
* **Multi-replica deployments** and load-balanced access to your pipeline
  service.
* **Fine-grained pod customization** (resources, tolerations, secrets,
  affinity, custom command/args, probes).
* **Cluster networking integrations** (e.g., exposing services via
  LoadBalancer, NodePort, or internal ClusterIP plus your own Ingress/mesh).

If you only need local development or single-node deployments, consider the
[local](local.md) or [docker](docker.md) deployer flavors instead.

## How to deploy it

1. Install the Kubernetes integration:

   ```bash
   zenml integration install kubernetes
   ```

2. Ensure your stack contains a container registry and an image builder that the
   Kubernetes cluster can access. Remote clusters require remote registries.

3. Configure access to your cluster. You can either:

   - Provide a kubeconfig context via `kubernetes_context`.
   - Run the client inside the cluster (`incluster=True`).
   - Link a [Kubernetes service connector](../../service-connectors/connector-types/kubernetes-cluster.md).

4. Register and activate the deployer:

   ```bash
   zenml deployer register k8s-deployer \
     --flavor=kubernetes \
     --kubernetes_namespace=zenml-deployments \

   zenml stack register prod-stack \
     -o default -a default \
     -c dockerhub \
     -D k8s-deployer \
     --set
   ```

   If you use a service connector:

   ```bash
   zenml service-connector register k8s-connector \
     --type kubernetes-cluster \
     --use-kubeconfig

   zenml deployer connect k8s-deployer --connector k8s-connector
   ```

## How to use it

Once the deployer is part of your active stack you can deploy pipelines or
snapshots exactly like with other flavors:

```bash
zenml pipeline deploy my_module.my_pipeline --deployment k8s-example
zenml deployment invoke k8s-example --json '{"parameters": {"name": "Ada"}}'
```

You can also configure deployer-specific settings directly on the pipeline:

```python
from zenml import pipeline, step
from zenml.integrations.kubernetes.deployers import KubernetesDeployerSettings


@step
def greet(name: str) -> str:
    return f"Hello {name}!"


@pipeline(
    settings={
        "deployer": KubernetesDeployerSettings(
            namespace="team-namespace",
            replicas=2,
            service_type="ClusterIP",
            service_annotations={"alb.ingress.kubernetes.io/scheme": "internet-facing"},
        )
    }
)
def greeting_pipeline(name: str = "ZenML") -> str:
    return greet(name=name)
```

## Configuration reference

The deployer combines two configuration layers:

- `KubernetesDeployerConfig` (component-level configuration):
  - `kubernetes_context`: kubeconfig context to use when no connector is
    linked. Required for out-of-cluster clients.
  - `incluster`: set to `True` if the client runs inside the target cluster.
  - `kubernetes_namespace`: default namespace for deployments (default
    `zenml-deployments`).
- `KubernetesDeployerSettings` (pipeline/deployment-level overrides):
  - **Networking**
    - `namespace`: override namespace per deployment.
    - `service_type`: `LoadBalancer`, `NodePort`, or `ClusterIP`.
    - `service_port`: exposed container port (default `8000`).
    - `node_port`: explicit NodePort (30000–32767) when using `NodePort`.
    - `session_affinity`: set to `ClientIP` for sticky sessions.
    - `load_balancer_ip`: pre-allocated LoadBalancer IP.
    - `load_balancer_source_ranges`: CIDR ranges allowed to reach the service.
    - `service_annotations`: attach provider-specific annotations (e.g. ALB,
      firewall rules).
  - **Ingress** (for production HTTP/HTTPS access)
    - `ingress_enabled`: create an Ingress resource (default `False`).
    - `ingress_class`: ingress controller class name (e.g., `nginx`, `traefik`).
    - `ingress_host`: hostname for the Ingress (e.g., `app.example.com`).
    - `ingress_path`: path prefix (default `/`).
    - `ingress_path_type`: `Prefix`, `Exact`, or `ImplementationSpecific`.
    - `ingress_tls_enabled`: enable TLS/HTTPS (default `False`).
    - `ingress_tls_secret_name`: Kubernetes Secret containing TLS certificate.
    - `ingress_annotations`: controller-specific annotations (rewrite rules, rate limits, etc.).
  - **Image & command**
    - `image_pull_policy`: `IfNotPresent`, `Always`, or `Never`.
    - `image_pull_secrets`: reference Kubernetes image pull secrets.
    - `command` / `args`: override container entrypoint/arguments.
  - **Health probes**
    - `readiness_probe_*` and `liveness_probe_*`: tune probe timings, thresholds,
      and timeouts.
  - **Authorization & customization**
    - `service_account_name`: run pods under a specific service account.
    - `labels` / `annotations`: attach metadata to all managed resources.
    - `pod_settings`: use
      [`KubernetesPodSettings`](../../orchestrators/kubernetes.md#customize-pod-specs)
      to mount volumes, set node selectors, tolerations, affinity rules, etc.

## Resource Configuration

You can specify the resource and scaling requirements for your pipeline deployment using the `ResourceSettings` class at the pipeline level:

```python
from zenml import pipeline, step
from zenml.config import ResourceSettings


@step
def greet(name: str) -> str:
    return f"Hello {name}!"


resource_settings = ResourceSettings(
    cpu_count=2,           # 2 CPU cores
    memory="4GB",          # 4 GB RAM
    min_replicas=1,        # Minimum 1 pod
    max_replicas=5,        # Maximum 5 pods (for autoscaling)
)

@pipeline(settings={"resources": resource_settings})
def greeting_pipeline(name: str = "ZenML") -> str:
    return greet(name=name)
```

If resource settings are not specified, the default values are:
* `cpu_count` defaults to 1 CPU core
* `memory` defaults to 2 GiB
* `min_replicas` defaults to 1
* `max_replicas` defaults to 1 (fixed scaling)

### Resource Mapping

The Kubernetes deployer converts `ResourceSettings` to Kubernetes resource requests and limits:

- **CPU**: The `cpu_count` value is used for both requests and limits. For values < 1, it's converted to millicores (e.g., 0.5 = "500m"). For values >= 1, integer values are used directly.
- **Memory**: The `memory` value is used for both requests and limits. ResourceSettings accepts formats like "2GB", "512Mi", etc. The deployer converts these to Kubernetes-native formats (Mi, Gi).
- **Replicas**: 
  - If `min_replicas` == `max_replicas`, a fixed number of pods is deployed
  - If they differ, `min_replicas` is used as the baseline (Horizontal Pod Autoscaler would be needed for actual autoscaling)
  - If only `max_replicas` is specified, it's used as a fixed value

### Additional Resource Settings

ResourceSettings also supports autoscaling configuration (though you'll need to configure HPA separately):

- `autoscaling_metric`: Metric to scale on ("cpu", "memory", "concurrency", or "rps")
- `autoscaling_target`: Target value for the metric (e.g., 70.0 for 70% CPU)
- `max_concurrency`: Maximum concurrent requests per pod

## RBAC requirements

The deployer (either via the service connector or the client credentials) must
be able to:

- Read, create, patch, and delete `Deployments`, `Services`, and `Pods` in the
  target namespace.
- Create, patch, and delete `Secrets` (used for environment variables and
  auth keys).
- Create, patch, and delete `Ingresses` when `ingress_enabled=True`
  (requires permissions on `networking.k8s.io/v1/Ingress` resources).
- Create namespaces when they do not exist, unless you pre-create them.
- If you rely on automatic service-account provisioning, create service
  accounts and role bindings (`create`, `patch`, `get`, `list` on
  `ServiceAccount` and `RoleBinding`).
- Read cluster nodes when using the `NodePort` service type (to expose IPs).

For production environments we recommend creating a dedicated service account
with minimal permissions scoped to the deployer namespace.

## Using Ingress Controllers

For production deployments, you can configure an Ingress resource to provide
HTTP/HTTPS access with custom domains, TLS termination, and advanced routing.
The Kubernetes deployer supports standard Kubernetes Ingress resources and works
with popular ingress controllers like nginx, Traefik, and cloud provider solutions.

### Basic Ingress Configuration

Enable ingress and specify your domain:

```python
from zenml import pipeline, step
from zenml.integrations.kubernetes.deployers import KubernetesDeployerSettings


@step
def greet(name: str) -> str:
    return f"Hello {name}!"


@pipeline(
    settings={
        "deployer": KubernetesDeployerSettings(
            service_type="ClusterIP",  # Use ClusterIP with Ingress
            ingress_enabled=True,
            ingress_class="nginx",
            ingress_host="my-app.example.com",
        )
    }
)
def greeting_pipeline(name: str = "ZenML") -> str:
    return greet(name=name)
```

### TLS/HTTPS Configuration

Enable TLS for secure HTTPS access:

```python
settings={
    "deployer": KubernetesDeployerSettings(
        service_type="ClusterIP",
        ingress_enabled=True,
        ingress_class="nginx",
        ingress_host="my-app.example.com",
        ingress_tls_enabled=True,
        ingress_tls_secret_name="my-app-tls",  # Must exist in namespace
    )
}
```

The TLS secret should be created separately:

```bash
kubectl create secret tls my-app-tls \
  --cert=path/to/tls.crt \
  --key=path/to/tls.key \
  -n <namespace>
```

Or use cert-manager for automatic certificate provisioning:

```python
settings={
    "deployer": KubernetesDeployerSettings(
        service_type="ClusterIP",
        ingress_enabled=True,
        ingress_class="nginx",
        ingress_host="my-app.example.com",
        ingress_tls_enabled=True,
        ingress_tls_secret_name="my-app-tls",
        ingress_annotations={
            "cert-manager.io/cluster-issuer": "letsencrypt-prod",
        },
    )
}
```

### Controller-Specific Annotations

Different ingress controllers support specific annotations for advanced features:

**nginx-ingress**:
```python
ingress_annotations={
    "nginx.ingress.kubernetes.io/rewrite-target": "/",
    "nginx.ingress.kubernetes.io/rate-limit": "100",
    "nginx.ingress.kubernetes.io/ssl-redirect": "true",
}
```

**Traefik**:
```python
ingress_annotations={
    "traefik.ingress.kubernetes.io/router.entrypoints": "websecure",
    "traefik.ingress.kubernetes.io/router.middlewares": "default-ratelimit@kubernetescrd",
}
```

**AWS ALB**:
```python
ingress_class="alb"
ingress_annotations={
    "alb.ingress.kubernetes.io/scheme": "internet-facing",
    "alb.ingress.kubernetes.io/target-type": "ip",
    "alb.ingress.kubernetes.io/certificate-arn": "arn:aws:acm:...",
}
```

### Path-Based Routing

Configure path prefixes for multi-service deployments:

```python
settings={
    "deployer": KubernetesDeployerSettings(
        ingress_enabled=True,
        ingress_host="api.example.com",
        ingress_path="/weather",  # Access at api.example.com/weather
        ingress_path_type="Prefix",
    )
}
```

### Limitations

The deployer currently creates standard Kubernetes Ingress resources
(networking.k8s.io/v1). For service mesh solutions like Istio that use different
APIs (Gateway/VirtualService), you'll need to create those resources separately
and use `service_type="ClusterIP"` to expose the service internally.

For end-to-end deployment workflows, see the
[deployment user guide](../../user-guide/production-guide/deployment.md).
