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
| Everything deleted (end of spike) | $0, plus a few cents/month for ECR image storage until repos are deleted |

The node group is created with `desiredSize=0`, so **creating it costs
nothing**. You pay only between "scale up" (part 2) and "scale down"
(part 6). A realistic full Stage-3 day is 4–8 GPU-hours ≈ **$5–10**.

The decided topology (Stage 0, Michael concurring): **no vLLM server** —
generation runs inside a per-iteration pipeline step via vLLM's offline
batch API, with the LoRA adapter passed per call. There is nothing extra
to deploy or keep warm. The runner-up topologies, in case this chafes in
practice, are documented at the bottom.

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
at most one `g6.2xlarge` (1× NVIDIA L4 24GB, 8 vCPU, 32GB RAM). Two
details do the heavy lifting:

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
  --scaling-config minSize=0,maxSize=1,desiredSize=0 \
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
  --scaling-config minSize=0,maxSize=1,desiredSize=1
```

Wait ~2–3 minutes, then check, in order:

```bash
# 1. The node joined and is Ready:
kubectl get nodes -l pool=gpu
# NAME                                          STATUS   ROLES    AGE   VERSION
# ip-10-10-x-x.eu-central-1.compute.internal    Ready    <none>   90s   v1.33.x-eks-...

# 2. The node advertises exactly one GPU (device plugin working):
kubectl get nodes -l pool=gpu \
  -o jsonpath='{.items[0].status.allocatable.nvidia\.com/gpu}'; echo
# 1                    <- if empty or missing: wrong AMI type, see troubleshooting

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

## Part 4 — The pipeline image (automatic, but know what to expect)

You don't build this one by hand. When `run.py` runs without `--dry-run`,
ZenML builds the pipeline image from the `DockerSettings` in
`k8s_settings.py`:

- parent image `vllm/vllm-openai:v0.24.0-x86_64-ubuntu2404` (torch, CUDA,
  and vLLM 0.24.0 preinstalled — verified to exist on Docker Hub);
- plus `trl==1.7.1`, `peft`, `datasets` and the example code on top;
- built for `linux/amd64` (cross-built on your Apple Silicon Mac) and
  pushed to the existing `zenml` ECR repository the stack already uses.

**Expect the first build to be slow**: ~10GB of parent layers pulled and
re-pushed, 20–45 minutes depending on your connection. Subsequent runs
reuse the build unless requirements change. If the cross-build is
painfully slow, the escape hatch is running the same command from any
x86_64 Linux box with docker + repo access.

## Part 5 — What runs where (already wired into the code)

No action needed — this is the map of what the settings in
`k8s_settings.py` + `pipelines/rl_spike_pipeline.py` do on the remote
stack. The orchestrator is **async** (`synchronous: False`), so `run.py`
returns as soon as the run is submitted; watch progress in the dashboard
or with `kubectl get pods -n michael -w`.

| Step | Pod | GPU | Image |
|---|---|---|---|
| orchestrator (pipeline function) | CPU pool `main` | no | pipeline image |
| `load_tasks`, `log_iteration_metrics` | inline in orchestrator pod | no | pipeline image |
| `init_lora` | isolated, GPU node | yes | pipeline image |
| `generate_rollouts` (vLLM batch) | isolated, GPU node | yes | pipeline image |
| `run_episode` × N (mapped) | isolated, CPU pool | no | pipeline image |
| ↳ each episode's sandbox session | sandbox pod, CPU pool | no | `zenml-rl-spike-sandbox:0.1` |
| `grpo_update` (TRL step) | isolated, GPU node | yes | pipeline image |

Because generation and training both request `nvidia.com/gpu: 1` and
there is exactly one GPU, they serialize on the node naturally — no
contention possible, some queueing expected (that's the measured cost of
the no-server topology, breakage log entry 2).

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
   python run.py --iterations 1 --group-size 2 --task-ids const_seven
   ```

   Healthy result: run completes; the two episodes have *different*
   completions (temperature sampling) with plausible rewards; grpo_update
   metadata shows a finite `grad_norm`; a new adapter artifact exists.
4. **STOP. Scale down (below) and hand back to Claude** — Stage 3 (smoke
   scale: 2 iterations × 5 tasks × group 2) starts from there, at STOP
   GATE 4 discipline.

## Part 7 — Shutting down (overnight, and forever)

**Overnight / between sessions — scale to zero** (node group stays,
definition is free, nothing bills):

```bash
aws eks update-nodegroup-config \
  --cluster-name eu-staging-cloud-infra-cluster \
  --nodegroup-name rl-spike-gpu \
  --scaling-config minSize=0,maxSize=1,desiredSize=0

# Verify the node is actually gone (~2 min):
kubectl get nodes -l pool=gpu
# "No resources found"    <- this is the $0.00/hr state

# Also check no RL pods are stuck consuming the CPU pool:
kubectl get pods -n michael | grep -v Completed
```

Do the scale-down even if a run is mid-flight and you're abandoning it —
a killed run zombifies on the server (breakage log entry 6) but costs
nothing; the GPU node costs $29/day.

**End of spike — full teardown:**

```bash
aws eks delete-nodegroup \
  --cluster-name eu-staging-cloud-infra-cluster \
  --nodegroup-name rl-spike-gpu
aws ecr delete-repository --repository-name zenml-rl-spike-sandbox --force
# The pipeline images live in the shared `zenml` ECR repo; leave those.
```

## Troubleshooting

- **GPU step pod `Pending` forever** → node not scaled up
  (`kubectl get nodes -l pool=gpu` empty), or the pod lacks the
  toleration (check it went through `GPU_STEP_SETTINGS`), or another pod
  holds the single GPU (`kubectl describe node <gpu-node> | grep -A5
  "Allocated resources"`).
- **`nvidia.com/gpu` missing from node allocatable** → node group was
  created with the wrong AMI type; it must be
  `BOTTLEROCKET_x86_64_NVIDIA`. Delete and recreate the node group.
- **`ErrImagePull` on sandbox pods** → the `zenml-rl-spike-sandbox:0.1`
  tag wasn't pushed, or was built for arm64 (rebuild with
  `--platform linux/amd64`).
- **CUDA OOM in `generate_rollouts` or `grpo_update`** → first check
  nothing else holds GPU memory (the two steps must not overlap — they
  can't, with one GPU). If genuinely OOM at 24GB: recreate the node group
  with `g6e.xlarge` (48GB L40S, $2.33/hr) — one flag change in part 1.
- **`run.py` exits immediately** → expected; the orchestrator is async.
  The run URL is printed; watch there or `kubectl get pods -n michael -w`.

## Runner-up topologies (documented per Stage 0 decision, not built)

1. **Deployer-hosted vLLM service** (the "keep it warm" fix, v1
   material): deploy a generation pipeline via the in-tree
   `KubernetesDeployer` as a long-lived FastAPI service whose `on_init`
   loads the vLLM engine once; episodes invoke it over HTTP; adapters are
   still passed per request by reference. Removes the per-iteration
   engine load, at the price of a GPU held 24/7 while deployed and an
   experimental component in the critical path.
2. **Long-lived raw vLLM server + hot adapter swap**: a plain K8s
   Deployment running `vllm serve` with
   `VLLM_ALLOW_RUNTIME_LORA_UPDATING=1`; after each `grpo_update`, POST
   `/v1/load_lora_adapter` (`load_inplace=true`) with the new adapter.
   Fastest serving, but lives entirely outside ZenML (no lineage, no
   lifecycle management) — exactly the gap breakage log entry 2 records.
