---
description: Deploying your pipelines to Kubernetes clusters.
---

# Kubernetes Deployer

[Kubernetes](https://kubernetes.io/) is the industry-standard container orchestration platform for deploying and managing containerized applications at scale. The Kubernetes deployer is a [deployer](./) flavor included in the ZenML Kubernetes integration that deploys your pipelines to any Kubernetes cluster as production-ready services.

{% hint style="warning" %}
This component is only meant to be used within the context of a [remote ZenML installation](https://docs.zenml.io/getting-started/deploying-zenml/). Usage with a local ZenML setup may lead to unexpected behavior!
{% endhint %}

## When to use it

You should use the Kubernetes deployer if:

* you already have a Kubernetes cluster (EKS, GKE, AKS, or self-managed).
* you need fine-grained control over deployment configuration (resources, networking, security).
* you want production-grade features like autoscaling, health probes, and high availability.
* you need to deploy to on-premises infrastructure or air-gapped environments.
* you want to leverage existing Kubernetes expertise and tooling in your organization.
* you need to integrate with existing Kubernetes resources (Ingress, NetworkPolicies, ServiceMonitors, etc.).

## How to deploy it

{% hint style="info" %}
Would you like to skip ahead and deploy a full ZenML cloud stack already, including a Kubernetes deployer? Check out the ZenML stack deployment guides for [AWS](https://docs.zenml.io/how-to/infrastructure-deployment/stack-deployment/deploy-a-cloud-stack-with-terraform), [GCP](https://docs.zenml.io/how-to/infrastructure-deployment/stack-deployment/deploy-a-cloud-stack-with-terraform), and [Azure](https://docs.zenml.io/how-to/infrastructure-deployment/stack-deployment/deploy-a-cloud-stack-with-terraform).
{% endhint %}

To use the Kubernetes deployer, you need:

* A running Kubernetes cluster (version 1.21 or higher recommended)
* Access credentials configured via `kubectl` or a service connector)

## How to use it

To use the Kubernetes deployer, you need:

*   The ZenML `kubernetes` integration installed. If you haven't done so, run

    ```shell
    zenml integration install kubernetes
    ```
* [Docker](https://www.docker.com) installed and running.
* A [remote artifact store](https://docs.zenml.io/stacks/artifact-stores/) as part of your stack.
* A [remote container registry](https://docs.zenml.io/stacks/container-registries/) as part of your stack.
* [Kubernetes cluster access](#kubernetes-access-and-permissions) either via `kubectl` or a service connector.

### Kubernetes access and permissions

You have two different options to provide cluster access to the Kubernetes deployer:

* use `kubectl` to authenticate locally with your Kubernetes cluster
* (recommended) configure [a Kubernetes Service Connector](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/kubernetes-service-connector) and link it to the Kubernetes deployer stack component.

#### Kubernetes Permissions

The Kubernetes deployer needs the following permissions in the target namespace:

* **Deployments**: `create`, `get`, `list`, `watch`, `update`, `delete`
* **Services**: `create`, `get`, `list`, `watch`, `update`, `delete`
* **Secrets**: `create`, `get`, `list`, `watch`, `update`, `delete`
* **Pods**: `get`, `list`, `watch` (for logs and status)
* **Namespaces**: `create`, `get` (if creating namespaces)

If using additional resources (Ingress, HPA, NetworkPolicy, etc.), you'll also need permissions for those resource types.

#### Configuration use-case: local kubectl with context

This configuration assumes you have configured `kubectl` to authenticate with your cluster (i.e. by running `kubectl config use-context <context-name>`). This is the easiest way to get started:

```shell
zenml deployer register <DEPLOYER_NAME> \
    --flavor=kubernetes \
    --kubernetes_context=<CONTEXT_NAME> \
    --kubernetes_namespace=zenml-deployments
```

{% hint style="warning" %}
This setup is not portable to other machines unless they have the same kubectl context configured. For production and team environments, use a service connector instead.
{% endhint %}

#### Configuration use-case: Kubernetes Service Connector

This is the recommended approach for production and team environments. It makes credentials portable and manageable:

```shell
# Register a Kubernetes service connector
zenml service-connector register <CONNECTOR_NAME> \
    --type kubernetes \
    --auth-method=token \
    --token=<YOUR_TOKEN> \
    --server=<CLUSTER_URL> \
    --certificate_authority=<CA_CERT_PATH> \
    --resource-type kubernetes-cluster

# Register the deployer and link it to the connector
zenml deployer register <DEPLOYER_NAME> \
    --flavor=kubernetes \
    --kubernetes_namespace=zenml-deployments \
    --connector <CONNECTOR_NAME>
```

See the [Kubernetes Service Connector documentation](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/kubernetes-service-connector) for more authentication methods including:
* Service account tokens
* Kubeconfig files
* Cloud provider authentication (EKS, GKE, AKS)

#### Configuration use-case: In-cluster deployment

If your ZenML server runs inside the same Kubernetes cluster where you want to deploy pipelines, you can use in-cluster authentication:

```shell
zenml deployer register <DEPLOYER_NAME> \
    --flavor=kubernetes \
    --kubernetes_namespace=zenml-deployments
```

This uses the service account token mounted into the pod running ZenML.

### Configuring the stack

With the deployer registered, you can use it in your active stack:

```shell
# Register and activate a stack with the new deployer
zenml stack register <STACK_NAME> -D <DEPLOYER_NAME> ... --set
```

{% hint style="info" %}
ZenML will build a Docker image called `<CONTAINER_REGISTRY_URI>/zenml:<PIPELINE_NAME>` and use it to deploy your pipeline as a Kubernetes Deployment with a Service. Check out [this page](https://docs.zenml.io/how-to/customize-docker-builds/) if you want to learn more about how ZenML builds these images and how you can customize them.
{% endhint %}

You can now [deploy any ZenML pipeline](https://docs.zenml.io/concepts/deployment) using the Kubernetes deployer:

```shell
zenml pipeline deploy --name my_deployment my_module.my_pipeline
```

## Advanced configuration

The Kubernetes deployer follows a progressive complexity model, allowing you to start simple and add configuration as needed:

### Level 1: Essential settings (80% of use cases)

Most deployments only need these basic settings:

```python
from zenml import pipeline, step
from zenml.integrations.kubernetes.flavors.kubernetes_deployer_flavor import (
    KubernetesDeployerSettings
)
from zenml.config import ResourceSettings

@step
def greet(name: str) -> str:
    return f"Hello {name}!"

# Basic deployment settings
settings = {
    "deployer": KubernetesDeployerSettings(
        namespace="my-namespace",
        service_type="LoadBalancer",  # or "NodePort", "ClusterIP"
        service_port=8000,
    ),
    "resources": ResourceSettings(
        cpu_count=1,
        memory="2GB",
        min_replicas=1,
        max_replicas=3,
    )
}

@pipeline(settings=settings)
def greet_pipeline(name: str = "World"):
    greet(name=name)
```

### Level 2: Production-ready configuration

For production deployments, add health probes, labels, and resource limits:

```python
settings = {
    "deployer": KubernetesDeployerSettings(
        namespace="production",
        service_type="ClusterIP",  # Use with Ingress
        service_port=8000,

        
        # Labels for organization
        labels={
            "environment": "production",
            "team": "ml-platform",
            "version": "1.0",
        },
        
        # Prometheus monitoring
        annotations={
            "prometheus.io/scrape": "true",
            "prometheus.io/port": "8000",
            "prometheus.io/path": "/metrics",
        },
    ),
    "resources": ResourceSettings(
        cpu_count=2,
        memory="4GB",
        min_replicas=2,
        max_replicas=10,
    )
}
```

### Level 3: Additional resources

Deploy additional Kubernetes resources alongside your main Deployment and Service (Ingress, HorizontalPodAutoscaler, PodDisruptionBudget, NetworkPolicy, etc.):

First, create a YAML file (e.g., `k8s-resources.yaml`) with your additional resources:

```yaml
# Ingress for domain-based routing
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-ingress
  namespace: {{namespace}}  # ZenML fills this
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  rules:
    - host: myapp.company.com  # Your domain
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: {{service_name}}  # ZenML fills this
                port:
                  number: {{service_port}}  # ZenML fills this

# HorizontalPodAutoscaler for autoscaling
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-hpa
  namespace: {{namespace}}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{deployment_name}}  # ZenML fills this
  minReplicas: {{replicas}}  # ZenML fills this
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70

# PodDisruptionBudget for high availability
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: my-pdb
  namespace: {{namespace}}
spec:
  minAvailable: 1
  selector:
    matchLabels:
      managed-by: {{labels['managed-by']}}
      zenml-deployment-id: {{labels['zenml-deployment-id']}}
```

Then reference this file in your deployment settings:

```python
settings = {
    "deployer": KubernetesDeployerSettings(
        additional_resources=[
            "./k8s-resources.yaml"
        ],
        strict_additional_resources=True,  # Fail if any resource fails to apply
        # ... other settings
    )
}
```

**Available template variables** for use in your YAML files:

* `{{namespace}}`: Kubernetes namespace
* `{{deployment_name}}` or `{{name}}`: Deployment name
* `{{service_name}}`: Service name (same as deployment name)
* `{{service_port}}`: Service port number
* `{{service_type}}`: Service type (LoadBalancer, NodePort, ClusterIP)
* `{{labels}}`: Dict of ZenML-managed labels
* `{{labels['managed-by']}}`: Always 'zenml'
* `{{labels['zenml-deployment-id']}}`: Deployment UUID
* `{{labels['zenml-deployment-name']}}`: Human-readable deployment name
* `{{replicas}}`: Configured replica count
* `{{image}}`: Container image
* `{{deployment_id}}`: Deployment UUID
* `{{annotations}}`: Pod annotations dict

{% hint style="warning" %}
**Important prerequisites:**
- **Ingress**: Requires an ingress controller (nginx, traefik, etc.) installed in your cluster
- **HPA**: Requires [metrics-server](https://github.com/kubernetes-sigs/metrics-server) installed
- **ServiceMonitor**: Requires [Prometheus Operator](https://prometheus-operator.dev/) CRDs installed
- **CRDs**: Any custom resources must have their CRDs installed beforehand
{% endhint %}

### Level 4: Custom Deployment and Service templates

For maximum control, you can completely override the built-in Deployment and Service templates by providing your own Jinja2 templates. This allows you to customize every aspect of the core Kubernetes resources that ZenML creates.

**When to use custom templates:**
* You need to add features not supported by the standard settings (init containers, sidecar containers, custom volume types)
* You want complete control over health probe configuration beyond the provided settings
* You need specific Kubernetes features for compliance or security requirements
* You're migrating existing Kubernetes manifests to ZenML and want to maintain the exact structure

**How it works:**

1. Create a directory for your custom templates (e.g., `~/.zenml/k8s-templates/`)
2. Add one or both of these files to override the built-in templates:
   - `deployment.yaml.j2` - Override the Deployment resource
   - `service.yaml.j2` - Override the Service resource
3. Configure the deployer to use your custom templates:

```python
settings = {
    "deployer": KubernetesDeployerSettings(
        custom_templates_dir="~/.zenml/k8s-templates/",
        # ... other settings
    )
}
```

**Available template variables:**

Your custom templates have access to all the same context variables as the built-in templates:

* `name`: Deployment/Service name (use `{{ name | k8s_name }}` filter)
* `namespace`: Kubernetes namespace
* `image`: Container image
* `replicas`: Number of replicas
* `labels`: Dict of labels (includes ZenML-managed labels)
* `annotations`: Dict of pod annotations
* `service_account_name`: Service account (if set)
* `image_pull_policy`: Image pull policy
* `image_pull_secrets`: List of image pull secret names
* `command`: Container command override (if set)
* `args`: Container args override (if set)
* `env`: Environment variables dict
* `resources`: Resource requests/limits dict
* `pod_settings`: KubernetesPodSettings object (if set)
* `service_port`: Service port number
* `service_type`: Service type (LoadBalancer, NodePort, ClusterIP)
* Health probe settings: `readiness_probe_path`, `readiness_probe_initial_delay`, etc.

**Example: Custom deployment template with init container**

Create `~/MyProject/k8s-templates/deployment.yaml.j2`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ name | k8s_name }}
  namespace: {{ namespace }}
  labels:
    app: {{ name | k8s_name }}
    managed-by: zenml
    {% if labels %}
    {% for key, value in labels.items() %}
    {{ key }}: {{ value | k8s_label_value | tojson }}
    {% endfor %}
    {% endif %}
spec:
  replicas: {{ replicas | default(1) }}
  selector:
    matchLabels:
      managed-by: zenml
      zenml-deployment-id: {{ labels.get('zenml-deployment-id') | tojson }}
  template:
    metadata:
      labels:
        app: {{ name | k8s_name }}
        managed-by: zenml
        {% if labels %}
        {% for key, value in labels.items() %}
        {{ key }}: {{ value | k8s_label_value | tojson }}
        {% endfor %}
        {% endif %}
    spec:
      {% if service_account_name %}
      serviceAccountName: {{ service_account_name }}
      {% endif %}
      
      # Custom init container
      initContainers:
      - name: init-setup
        image: busybox:1.28
        command: ['sh', '-c', 'echo "Initializing..." && sleep 5']
      
      containers:
      - name: {{ name | k8s_name }}
        image: {{ image }}
        {% if command %}
        command: {{ command | to_json }}
        {% endif %}
        {% if args %}
        args: {{ args | to_json }}
        {% endif %}
        ports:
        - containerPort: {{ service_port }}
          name: http
        env:
        {% for key, value in env.items() %}
        - name: {{ key }}
          value: {{ value | tojson }}
        {% endfor %}
        {% if resources %}
        resources: {{ resources | to_yaml | indent(10) }}
        {% endif %}
        readinessProbe:
          httpGet:
            path: {{ readiness_probe_path }}
            port: {{ service_port }}
          initialDelaySeconds: {{ readiness_probe_initial_delay }}
          periodSeconds: {{ readiness_probe_period }}
        livenessProbe:
          httpGet:
            path: {{ liveness_probe_path }}
            port: {{ service_port }}
          initialDelaySeconds: {{ liveness_probe_initial_delay }}
          periodSeconds: {{ liveness_probe_period }}
```

{% hint style="info" %}
**Tip**: Start with ZenML's built-in templates as a reference. You can find them in the ZenML repository at `src/zenml/integrations/kubernetes/templates/`. Copy and modify them for your needs.
{% endhint %}

{% hint style="warning" %}
When using custom templates, you're responsible for maintaining compatibility with ZenML's deployment lifecycle. Ensure your templates:
- Use the correct label selectors (`zenml-deployment-id`, `managed-by: zenml`)
- Expose the correct container port (`{{ service_port }}`)
- Include health probes for proper deployment tracking
- Pass through environment variables (`{{ env }}`)
{% endhint %}

### Complete settings reference

For a complete list of all available settings, see the `KubernetesDeployerSettings` class. Here's a comprehensive overview organized by category:

**Basic Settings** (common to all Deployers):
* `auth_key`: User-defined authentication key for deployment API calls
* `generate_auth_key`: Whether to generate a random authentication key
* `lcm_timeout`: Maximum time in seconds to wait for deployment lifecycle operations

**Essential Settings**:
* `namespace`: Kubernetes namespace for the deployment (defaults to deployer's `kubernetes_namespace`)
* `service_type`: How to expose the service - `LoadBalancer`, `NodePort`, or `ClusterIP` (default: `LoadBalancer`)
* `service_port`: Port to expose on the service (default: `8000`)
* `image_pull_policy`: When to pull images - `Always`, `IfNotPresent`, or `Never` (default: `IfNotPresent`)
* `labels`: Additional labels to apply to all resources
* `annotations`: Annotations to add to pod resources

**Container Configuration**:
* `command`: Override container command/entrypoint
* `args`: Override container args
* `service_account_name`: Kubernetes service account for pods
* `image_pull_secrets`: List of secret names for pulling private images

**Health Probes**:
* `readiness_probe_path`: HTTP path for readiness probe (default: `/api/health`)
* `readiness_probe_initial_delay`: Initial delay in seconds (default: `10`)
* `readiness_probe_period`: Probe interval in seconds (default: `10`)
* `readiness_probe_timeout`: Probe timeout in seconds (default: `5`)
* `readiness_probe_failure_threshold`: Failures before marking pod not ready (default: `3`)
* `liveness_probe_path`: HTTP path for liveness probe (default: `/api/health`)
* `liveness_probe_initial_delay`: Initial delay in seconds (default: `30`)
* `liveness_probe_period`: Probe interval in seconds (default: `10`)
* `liveness_probe_timeout`: Probe timeout in seconds (default: `5`)
* `liveness_probe_failure_threshold`: Failures before restarting pod (default: `3`)

**Advanced Settings**:
* `pod_settings`: Advanced pod configuration (see `KubernetesPodSettings`)
* `additional_resources`: List of paths to YAML files with additional K8s resources
* `strict_additional_resources`: If `True`, fail deployment if any additional resource fails (default: `True`)
* `custom_templates_dir`: Path to directory with custom Jinja2 templates

**Internal Settings**:
* `wait_for_load_balancer_timeout`: Timeout for LoadBalancer IP assignment (default: `150` seconds, `0` to skip)
* `deployment_ready_check_interval`: Interval between readiness checks (default: `2` seconds)

Check out [this docs page](https://docs.zenml.io/concepts/steps_and_pipelines/configuration) for more information on how to specify settings.


## Troubleshooting

### Deployment stuck in pending state

Check pod events and logs:

```shell
# Get deployment info
zenml deployment describe my-deployment

# Follow logs
zenml deployment logs my-deployment -f

# Check Kubernetes resources directly
kubectl get pods -n <namespace>
kubectl describe pod <pod-name> -n <namespace>
```

Common causes:
* Insufficient cluster resources
* Image pull errors (check image_pull_secrets)
* Node selector/affinity constraints not satisfied
* PersistentVolumeClaim pending

### LoadBalancer not getting external IP

If using `LoadBalancer` service type and it stays `<pending>`:

* Check if your cluster supports LoadBalancer (cloud providers usually do, local clusters usually don't)
* For local clusters, use `NodePort` instead
* For production without LoadBalancer support, use `ClusterIP` with an Ingress

### Additional resources failing to apply

If using `strict_additional_resources=True` and deployment fails:

```shell
# Check which resource failed
zenml deployment describe my-deployment

# Validate resources manually
kubectl apply --dry-run=client -f k8s-resources.yaml
```

Common issues:
* Missing CRDs (install required operators)
* Missing cluster components (metrics-server for HPA, ingress controller for Ingress)
* Invalid resource references (check template variables)

### Image pull errors

If pods can't pull the container image:

* Verify image exists in registry: `docker pull <image>`
* Check `image_pull_secrets` are configured correctly
* Verify service account has access to registry
* Check image pull policy (`IfNotPresent` vs `Always`)

## Best practices

1. **Use service connectors** in production for portable, manageable credentials
2. **Always configure health probes** for production deployments
3. **Use Ingress with ClusterIP** instead of LoadBalancer for cost and flexibility
4. **Use labels and annotations** for organization, monitoring, and cost tracking
5. **Configure resource limits** to prevent resource exhaustion
6. **Use HPA** for autoscaling based on actual load
7. **Configure PodDisruptionBudget** for high availability during cluster updates
8. **Keep additional resources in version control** alongside your pipeline code

