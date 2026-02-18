---
description: Deploying your pipelines to Run:AI inference workloads with fractional GPUs.
---

# Run:AI Deployer

The Run:AI deployer is a [deployer](./) flavor provided by the Run:AI integration. It provisions ZenML pipeline deployments as Run:AI inference workloads, giving you GPU (or fractional GPU) serving with Run:AI autoscaling and scheduling.

## When to use it

Use the Run:AI deployer if:

- you already run workloads on Run:AI and want the same control plane for inference services,
- you need fractional GPU sharing (`gpu_portion_request`) to maximize GPU utilization,
- you want Run:AI autoscaling for pipeline-based inference endpoints,
- you prefer a managed control plane instead of running your own Kubernetes ingress.

## Prerequisites

- Install the integration: `zenml integration install runai`
- A Run:AI tenant (SaaS or self-hosted) with:
  - Client ID / Client Secret generated under Settings -> Applications
  - a project (and optional cluster) with quota for the GPUs/CPUs you will request
- Docker running locally (ZenML builds a container image for the deployment)
- A remote artifact store and container registry in your stack that both the deployer and Run:AI can reach

## Configure and register

Register the stack component with your Run:AI credentials and control-plane URL (example uses flavor name `runai`):

```bash
zenml deployer register runai-deployer \
  --flavor=runai \
  --client_id=<RUNAI_CLIENT_ID> \
  --client_secret=<RUNAI_CLIENT_SECRET> \
  --runai_base_url=https://<org>.run.ai \
  --project_name=<RUNAI_PROJECT> \
  --cluster_name=<OPTIONAL_CLUSTER>

zenml stack register runai-stack \
  -a <ARTIFACT_STORE> \
  -c <CONTAINER_REGISTRY> \
  -o <ORCHESTRATOR> \
  -D runai-deployer --set
```

## Deploy a pipeline

After the stack is active, deploy any pipeline as an inference service:

```bash
zenml pipeline deploy pipelines.inference_pipeline --name runai-service
```

The deployer builds a container image, uploads it to your registry, and creates a Run:AI inference workload. The endpoint URL is returned once the workload is running.

## Settings reference

**Component configuration (`RunAIDeployerConfig`):**

- `client_id`, `client_secret`: Run:AI application credentials (required).
- `runai_base_url`: Control-plane URL, e.g., `https://org.run.ai` (required).
- `project_name`: Run:AI project to submit workloads to (required).
- `cluster_name`: Optional cluster override (project default is used if omitted).
- `image_pull_secret_name`: Optional Run:AI image pull secret for private registries.

**Per-deployment settings (`RunAIDeployerSettings`):**

- Basic deployer settings:
  - `auth_key`: A user-defined authentication key to use to authenticate with deployment API calls.
  - `generate_auth_key`: Whether to generate and use a random authentication key instead of the user-defined one.
  - `lcm_timeout`: Maximum time in seconds to wait for deployment lifecycle operations.
- Compute:
  - `gpu_devices_request`, `gpu_request_type` (`portion` or `memory`), `gpu_portion_request`, `gpu_memory_request`
  - `cpu_core_request`, `cpu_memory_request`
- Scaling:
  - `min_replicas`, `max_replicas`
  - `autoscaling_metric`, `autoscaling_metric_threshold`
- Scheduling:
  - `node_pools`, `node_type`
- Metadata and runtime:
  - `labels`, `annotations`, `environment_variables`, `workload_name_prefix`

Set these in your pipeline via the `deployer` settings section or CLI `--settings` file.

## Troubleshooting

- **401 / 404** from Run:AI: verify `client_id` / `client_secret`, project name, and that the control-plane URL is correct.
- **503 errors**: temporary Run:AI control-plane unavailability or networking issues. Retry; if persistent, check your org's Run:AI status and outbound network/proxy settings.
- **Image pull errors**: ensure the container registry is reachable from Run:AI and configure `image_pull_secret_name` if the registry is private.
