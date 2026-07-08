# GPU setup for the RL spike (Stage 2 — instructions for Alex)

This document takes the staging EKS cluster from "no GPU anywhere" to "the
RL pipeline's GPU steps run", in five parts plus a smoke sequence and —
importantly — **how to turn it all off** so nothing bills overnight.

Every cluster-specific value in here (cluster name, node role ARN, subnets,
ECR URI, namespace, prices) was read live from the account on 2026-07-08
with the `zenml-dev-power` profile, not from memory. ZenML settings
snippets follow the [Kubernetes orchestrator docs](https://docs.zenml.io/stacks/stack-components/orchestrators/kubernetes)
(pod_settings → resources/node_selectors/tolerations) and
[containerization docs](https://docs.zenml.io/concepts/containerization)
(DockerSettings → parent_image/requirements), cross-checked against the
code on this branch.

## Cost summary (read this first)

| State | Cost |
|---|---|
| GPU node group exists, scaled to **0** | **$0.00/hr** — a node group definition is free |
| GPU node scaled to **1** | **$1.22/hr** (`g6.2xlarge`, on-demand, eu-central-1 — from the AWS Pricing API) |
| GPU nodes scaled to **2** | **$2.44/hr** — needed for warm-vLLM mode: one GPU serves rollouts while the other trains |
| Everything deleted (end of spike) | $0, plus a few cents/month for ECR image storage until repos are deleted |

The node group is created with `desiredSize=0`, so **creating it costs
nothing**. You pay only between "scale up" (part 2) and "scale down"
(part 6). A realistic one-GPU offline Stage-3 day is 4–8 GPU-hours ≈
**$5–10**; warm-vLLM mode roughly doubles that while both nodes are up.

There are now two supported spike topologies:

- **`--serving-mode offline`**: the original one-GPU proof path. Generation
  runs inside a per-iteration pipeline step via vLLM's offline batch API,
  with the LoRA adapter passed per call. This pays a vLLM cold-load every
  iteration but is the smallest thing to smoke-test.
- **`--serving-mode warm_vllm`**: the agreed next path after the Michael
  discussion. A raw Kubernetes vLLM Deployment stays warm on GPU 1,
  `grpo_update` trains on GPU 2, and a ZenML step hot-loads each new LoRA
  adapter artifact into the server via `/v1/load_lora_adapter`.

## Prerequisites (each fresh terminal session)

```bash
aws sso login --profile zenml-dev-power
export AWS_PROFILE=zenml-dev-power AWS_REGION=eu-central-1

# kubectl context for the staging cluster (yours is already configured
# as `snapshot-startup-eu-staging`; recreate it with:)
aws eks update-kubeconfig --name eu-staging-cloud-infra-cluster

# docker login for ECR pushes (parts 3-4):
aws ecr get-login-password | docker login --username AWS \
  --password-stdin 339712793861.dkr.ecr.eu-central-1.amazonaws.com

# ZenML: staging Pro server, rl-spike project, remote stack:
zenml login dev --pro-api-url https://staging.cloudapi.zenml.io/
zenml project set rl-spike
zenml stack set kubernetes_aws
```

## Part 1 — Create the GPU node group (one-time, costs nothing while at 0)

What this creates: a managed node group named `rl-spike-gpu` that can hold
at most two `g6.2xlarge` nodes (each node: 1× NVIDIA L4 24GB, 8 vCPU,
32GB RAM). One node is enough for `--serving-mode offline`; two nodes are
needed for `--serving-mode warm_vllm`. Two details do the heavy lifting:

- **AMI `BOTTLEROCKET_x86_64_NVIDIA`** — the NVIDIA variant of the
  Bottlerocket OS the cluster already runs. It ships the NVIDIA driver
  *and* the device plugin baked in, so there is **no driver DaemonSet to
  install**: as soon as the node joins, it advertises `nvidia.com/gpu: 1`.
- **Taint `pool=gpu:NoSchedule`** — nothing lands on the GPU node unless
  it explicitly tolerates the taint (our GPU steps do, via
  `k8s_settings.py`). Without it, random cluster pods would pin the
  expensive node busy.

The role ARN and subnets below are reused from the existing `main` node
group (read via `aws eks describe-nodegroup` on 2026-07-08). Heads-up for
cluster hygiene: the existing node groups are Terraform-managed; this one
is deliberately created outside Terraform for the spike and deleted
afterwards — worth a one-line heads-up to whoever owns the staging
Terraform.

```bash
aws eks create-nodegroup \
  --cluster-name eu-staging-cloud-infra-cluster \
  --nodegroup-name rl-spike-gpu \
  --node-role arn:aws:iam::339712793861:role/main-eks-node-group-20250509075315497500000004 \
  --subnets subnet-0dad0dd1b71003af8 subnet-06b905e9aa0d6ddd0 \
  --instance-types g6.2xlarge \
  --ami-type BOTTLEROCKET_x86_64_NVIDIA \
  --capacity-type ON_DEMAND \
  --disk-size 100 \
  --scaling-config minSize=0,maxSize=2,desiredSize=0 \
  --labels pool=gpu \
  --taints key=pool,value=gpu,effect=NO_SCHEDULE
```

(`--disk-size 100`: the pipeline image is large — vLLM + CUDA layers are
~10GB compressed — and Bottlerocket's default data volume would fill up.)

**Verify (healthy output shown):**

```bash
aws eks describe-nodegroup --cluster-name eu-staging-cloud-infra-cluster \
  --nodegroup-name rl-spike-gpu --query 'nodegroup.status'
# "ACTIVE"        <- takes ~2 minutes; "CREATING" until then
```

If creation fails with an insufficient-capacity error for an AZ, check
which AZs currently offer g6.2xlarge and recreate with just that subnet:
`aws ec2 describe-instance-type-offerings --location-type availability-zone
--filters Name=instance-type,Values=g6.2xlarge`.

## Part 2 — Scale up and verify the GPU is really there

**This is the moment billing starts ($1.22/hr).**

```bash
aws eks update-nodegroup-config \
  --cluster-name eu-staging-cloud-infra-cluster \
  --nodegroup-name rl-spike-gpu \
  --scaling-config minSize=0,maxSize=2,desiredSize=2
```

Wait ~2–3 minutes, then check, in order:

```bash
# 1. The node joined and is Ready:
kubectl get nodes -l pool=gpu
# NAME                                          STATUS   ROLES    AGE   VERSION
# ip-10-10-x-x.eu-central-1.compute.internal    Ready    <none>   90s   v1.33.x-eks-...

# 2. Each node advertises exactly one GPU (device plugin working):
kubectl get nodes -l pool=gpu \
  -o jsonpath='{range .items[*]}{.metadata.name}{": "}{.status.allocatable.nvidia\.com/gpu}{"\n"}{end}'
# ip-...: 1            <- if empty or missing: wrong AMI type, see troubleshooting

# 3. A raw pod can actually run nvidia-smi (driver working end-to-end):
kubectl run gpu-probe --rm -it --restart=Never \
  --image=nvidia/cuda:12.4.1-base-ubuntu22.04 \
  --overrides='{"spec":{"nodeSelector":{"pool":"gpu"},"tolerations":[{"key":"pool","operator":"Equal","value":"gpu","effect":"NoSchedule"}],"containers":[{"name":"gpu-probe","image":"nvidia/cuda:12.4.1-base-ubuntu22.04","command":["nvidia-smi"],"resources":{"limits":{"nvidia.com/gpu":"1"}}}]}}' \
  -n michael
# Expect the classic nvidia-smi table showing "NVIDIA L4" and "24GB".
```

All three green → the infrastructure layer is done.

## Part 3 — Build and push the sandbox image (one-time)

Why: every `run_episode` step opens a Kubernetes sandbox session pod
(namespace `michael`, per the stack's sandbox component). The sandbox
flavor's default image is `python:3.11-slim`, which cannot run our
in-sandbox scorer — the scorer executes the generated pipeline against a
throwaway local ZenML store, so **zenml must be preinstalled in the
sandbox image** (installing it per-episode would add ~1 min × 400
episodes).

```bash
aws ecr create-repository --repository-name zenml-rl-spike-sandbox

cat > /tmp/Dockerfile.sandbox <<'EOF'
FROM python:3.11-slim
# The sandbox runs generated toy pipelines against a local sqlite store;
# zenml[server] not needed. Pin to the server's version line.
RUN pip install --no-cache-dir "zenml==0.96.1"
EOF

# --platform matters: your Mac is arm64, the cluster is x86_64.
docker build --platform linux/amd64 \
  -t 339712793861.dkr.ecr.eu-central-1.amazonaws.com/zenml-rl-spike-sandbox:0.1 \
  -f /tmp/Dockerfile.sandbox /tmp
docker push 339712793861.dkr.ecr.eu-central-1.amazonaws.com/zenml-rl-spike-sandbox:0.1
```

This image URI is already referenced as `SANDBOX_IMAGE` in
`k8s_settings.py`; if you tag it differently, update that constant.

## Part 3b — RBAC for warm-vLLM lifecycle control

Warm mode creates and deletes raw Kubernetes resources from inside ZenML
steps. The service account used by the orchestrator/step pods must be able
to manage Deployments and Services and exec into the vLLM pod. The default
Kubernetes orchestrator service account is `zenml-service-account`; if your
stack uses a different one, update `VLLM_SERVICE_ACCOUNT_NAME` in
`k8s_settings.py` and bind that account instead.

```bash
cat <<'EOF' | kubectl apply -n michael -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: rl-spike-vllm-manager
rules:
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list", "create", "patch", "delete"]
  - apiGroups: [""]
    resources: ["services", "pods"]
    verbs: ["get", "list", "create", "patch", "delete"]
  - apiGroups: [""]
    resources: ["pods/exec"]
    verbs: ["create", "get"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: rl-spike-vllm-manager
subjects:
  - kind: ServiceAccount
    name: zenml-service-account
    namespace: michael
roleRef:
  kind: Role
  name: rl-spike-vllm-manager
  apiGroup: rbac.authorization.k8s.io
EOF
```

That same service account also needs whatever artifact-store access the
adapter materialization helper needs. For the current staging S3 artifact
store, the warm-vLLM server image includes `zenml[s3fs]`; the pod identity
still needs AWS credentials or an IRSA/node role that can read the bucket.

## Part 4 — The pipeline image (automatic, but know what to expect)

You don't build this one by hand. When `run.py` runs without `--dry-run`,
ZenML builds the pipeline image from the `DockerSettings` in
`k8s_settings.py`:

- parent image `vllm/vllm-openai:v0.24.0-x86_64-ubuntu2404` (torch, CUDA,
  and vLLM 0.24.0 preinstalled — verified to exist on Docker Hub);
- plus `trl==1.7.1`, `peft`, `datasets`, `kubernetes` and the example code on top;
- built for `linux/amd64` (cross-built on your Apple Silicon Mac) and
  pushed to the existing `zenml` ECR repository the stack already uses.

**Expect the first build to be slow**: ~10GB of parent layers pulled and
re-pushed, 20–45 minutes depending on your connection. Subsequent runs
reuse the build unless requirements change. If the cross-build is
painfully slow, the escape hatch is running the same command from any
x86_64 Linux box with docker + repo access.

## Part 4b — Build the warm-vLLM server image (for `--serving-mode warm_vllm`)

Warm mode creates a raw Kubernetes Deployment whose pod later receives an
exec call from `load_adapter_into_vllm`. That exec helper imports
`zenml.io.fileio` and copies the ZenML `Path` artifact archive from the
active artifact store into `/adapters/<adapter-name>`. The bare vLLM image
has vLLM, but not necessarily ZenML's artifact-store dependencies, so build
one thin derivative:

```bash
aws ecr create-repository --repository-name zenml-rl-spike-vllm-server

cat > /tmp/Dockerfile.vllm-server <<'EOF'
FROM vllm/vllm-openai:v0.24.0-x86_64-ubuntu2404
RUN apt-get update && apt-get install -y --no-install-recommends python-is-python3 \
  && rm -rf /var/lib/apt/lists/*
RUN python -m pip install --no-cache-dir "zenml[s3fs]==0.96.1"
EOF

docker build --platform linux/amd64 \
  -t 339712793861.dkr.ecr.eu-central-1.amazonaws.com/zenml-rl-spike-vllm-server:0.1 \
  -f /tmp/Dockerfile.vllm-server /tmp
docker push 339712793861.dkr.ecr.eu-central-1.amazonaws.com/zenml-rl-spike-vllm-server:0.1
```

If the stack uses a non-S3 artifact store later, change the extra in that
Dockerfile (`zenml[gcsfs]`, etc.) and update `VLLM_SERVER_IMAGE` in
`k8s_settings.py` if you tag it differently.

## Part 5 — What runs where (already wired into the code)

No action needed — this is the map of what the settings in
`k8s_settings.py` + `pipelines/rl_spike_pipeline.py` do on the remote
stack. The orchestrator is **async** (`synchronous: False`), so `run.py`
returns as soon as the run is submitted; watch progress in the dashboard
or with `kubectl get pods -n michael -w`.

| Step | Pod | GPU | Image |
|---|---|---|---|
| orchestrator (pipeline function) | GPU pool, no GPU requested | no | pipeline image |
| `load_tasks`, `log_iteration_metrics` | inline in orchestrator pod | no | pipeline image |
| `init_lora` | isolated, GPU node | yes | pipeline image |
| `generate_rollouts` (offline mode: vLLM batch) | isolated, GPU node | yes | pipeline image |
| `ensure_vllm_server` (warm mode) | orchestrator/step pod creates raw K8s Deployment + Service | no | pipeline image |
| raw vLLM server Deployment (warm mode) | GPU pool | yes, continuously | `VLLM_SERVER_IMAGE` |
| `load_adapter_into_vllm` (warm mode) | control step execs into vLLM pod and POSTs `/v1/load_lora_adapter` | no | pipeline image |
| `generate_rollouts_from_endpoint` (warm mode) | HTTP client step | no | pipeline image |
| `delete_vllm_server` (warm mode) | cleanup step deletes raw Deployment + Service on normal completion | no | pipeline image |
| `run_episode` × N (mapped) | isolated, CPU pool | no | pipeline image |
| ↳ each episode's sandbox session | sandbox pod, CPU pool | no | `zenml-rl-spike-sandbox:0.1` |
| `grpo_update` (TRL step) | isolated, GPU node | yes | pipeline image |

In `offline` mode, generation and training both request `nvidia.com/gpu: 1`; with one node they serialize naturally. In `warm_vllm` mode, the vLLM Deployment holds one GPU for the run while `grpo_update` needs another GPU, so scale the node group to two nodes before trying it.

## Part 6 — Smoke sequence (run by hand, in this order, then stop)

1. **Scale up** (part 2) and verify the three checks pass.
2. **GPU pipeline smoke** — one step that prints `nvidia-smi` from inside
   a ZenML-launched pod, using the exact same image/settings as the real
   pipeline:

   ```bash
   cd examples/rl_spike
   python gpu_smoke.py     # triggers the big image build on first run
   ```

   Green run in the dashboard + the `gpu_check` step's output artifact
   showing an L4 → image build, ECR, scheduling, tolerations, and CUDA
   all work.
3. **One real mini-iteration** — real Qwen3-4B via vLLM, 1 task, 2
   completions, 2 sandbox episodes, 1 real GRPO step:

   ```bash
   python run.py --iterations 1 --group-size 2 --task-ids const_seven \
     --serving-mode offline
   ```

   Healthy result: run completes; the two episodes have *different*
   completions (temperature sampling) with plausible rewards; grpo_update
   metadata shows a finite `grad_norm`; a new adapter artifact exists.
4. **Warm-vLLM mini-iteration** — only after the offline mini-iteration is green and the node group is at desiredSize=2. Do not run two warm-vLLM runs in the same namespace at once; the Deployment and Service names are fixed for the spike.

   ```bash
   python run.py --iterations 1 --group-size 2 --task-ids const_seven \
     --serving-mode warm_vllm
   ```

   Healthy result: `ensure_vllm_server` creates or patches the raw vLLM Deployment, `load_adapter_into_vllm` records the ZenML adapter artifact URI and loaded adapter name, `generate_rollouts_from_endpoint` gets two completions from the warm server, `grpo_update` still trains on the second GPU, and `delete_vllm_server` removes the raw Deployment/Service at the end of a successful run.
5. **STOP. Scale down (below)** — Stage 3 (smoke scale: 2 iterations × 5 tasks × group 2) starts from there, at STOP GATE 4 discipline.

## Part 7 — Shutting down (overnight, and forever)

**Overnight / between sessions — scale to zero** (node group stays,
definition is free, nothing bills):

```bash
aws eks update-nodegroup-config \
  --cluster-name eu-staging-cloud-infra-cluster \
  --nodegroup-name rl-spike-gpu \
  --scaling-config minSize=0,maxSize=2,desiredSize=0

# Verify the node is actually gone (~2 min):
kubectl get nodes -l pool=gpu
# "No resources found"    <- this is the $0.00/hr state

# Also check no RL pods are stuck consuming the CPU pool:
kubectl get pods -n michael | grep -v Completed
```

Do the scale-down even if a run is mid-flight and you're abandoning it —
a killed run may never reach `delete_vllm_server`, and one GPU node costs
$29/day; two warm-mode nodes cost roughly $58/day.

**End of spike — full teardown:**

```bash
aws eks delete-nodegroup \
  --cluster-name eu-staging-cloud-infra-cluster \
  --nodegroup-name rl-spike-gpu
aws ecr delete-repository --repository-name zenml-rl-spike-sandbox --force
aws ecr delete-repository --repository-name zenml-rl-spike-vllm-server --force
# The pipeline images live in the shared `zenml` ECR repo; leave those.
```

## Troubleshooting

- **GPU step pod `Pending` forever** → node not scaled up
  (`kubectl get nodes -l pool=gpu` empty), or the pod lacks the
  toleration (check it went through `GPU_STEP_SETTINGS`), or another pod
  already holds the GPU (`kubectl describe node <gpu-node> | grep -A5
  "Allocated resources"`). In warm mode, remember that the vLLM
  Deployment intentionally holds one GPU, so training needs a second node.
- **`nvidia.com/gpu` missing from node allocatable** → node group was
  created with the wrong AMI type; it must be
  `BOTTLEROCKET_x86_64_NVIDIA`. Delete and recreate the node group.
- **`ErrImagePull` on sandbox pods** → the `zenml-rl-spike-sandbox:0.1`
  tag wasn't pushed, or was built for arm64 (rebuild with
  `--platform linux/amd64`).
- **CUDA OOM in `generate_rollouts`, the vLLM Deployment, or `grpo_update`** → first check whether another pod holds GPU memory. If genuinely OOM at 24GB: recreate the node group with `g6e.xlarge` (48GB L40S, $2.33/hr) — one flag change in part 1.
- **`run.py` exits immediately** → expected; the orchestrator is async.
  The run URL is printed; watch there or `kubectl get pods -n michael -w`.

## Serving topology status

`--serving-mode warm_vllm` now implements the long-lived raw vLLM server
path directly: a ZenML step creates or patches the Kubernetes Deployment,
then later ZenML steps hot-load the exact LoRA adapter artifacts emitted by
`init_lora` / `grpo_update`. The serving pod is still raw Kubernetes, not a
ZenML model deployer; this is deliberate because the deployer abstraction
is not production-grade for this RL serving case.

The remaining alternative to revisit later is a deployer-hosted vLLM
service. That would make the server lifecycle more ZenML-shaped, but it
would put an experimental deployer component in the critical path and
still needs a clear story for hot-loading adapter artifacts without losing
lineage.
