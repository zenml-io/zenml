# Evaluate and train terminal agents with ZenML

This example runs a real ZenML pipeline: prepare and qualify terminal tasks, evaluate an agent, and produce an `HTMLString` report. ZenML records task provenance and episode evidence as artifacts so a later run can compare against a previous evaluation. A separate bounded RL pipeline uses SkyRL to train a LoRA adapter and produce a fresh before/after comparison.

The default is a reviewed ten-task subset of [Endless Terminals](https://huggingface.co/datasets/obiwan96/endless-terminals), pinned in `tasks.json`. This small subset is a starting point for evaluation, not a representative benchmark.

## Modal training pilot

For unchanged-model screening, `run_modal_baseline.py --bundle BUNDLE --config CONFIG` accepts a `BaselineConfig` JSON containing up to 20 task IDs and an immutable `modal_agent_images` entry for every task. Use the same controller, service, and sandbox settings as the training pilot. Each task must pass initial-state, reference, and no-op checks on Modal before evaluation; rejected tasks remain visible in qualification evidence. The baseline uses one zero-update sampler for three round-robin attempts per accepted task, preserves partial results at the service deadline, and reports infrastructure failures separately from task failures. The GPU lifetime remains capped at 90 minutes, including startup. CPU qualification has a 60-minute step timeout, and the overall submission has a three-hour timeout.

A verified DNS extraction run on September 8, 2026 used Qwen2.5-7B-Instruct on one H200. Ten evaluation attempts passed 9/10 before training and 10/10 afterward. Four training groups of eight scored 6/8, 6/8, 8/8, and 8/8; the first two groups produced optimizer updates and the equal-reward groups skipped updates. All 392 exported adapter tensors changed, file hashes matched, and all 52 model episodes and cloud resources cleaned up. These are observed counts on the training task, not evidence of held-out generalization or a statistically established improvement.

Set `training.evaluation_attempts` to repeat each selected task before and after training; it defaults to one and accepts up to 20. The report matches task and attempt IDs. The service reserves time for final evaluation and export using all evaluation interaction budgets and observed overhead; this is a heuristic, and infrastructure stalls can still exhaust the hard lifetime. Final evaluation runs before export so a transfer failure preserves both evaluations. Native checkpoint transfers retry transient errors up to three times, with a 420-second parent-process deadline.

`run_modal_training.py` runs the orchestrator, terminal sandboxes and GPU training service in the workspace and environment specified by `service.workspace` and `service.modal_environment`. Configure both Modal stack components with explicit credentials for that workspace and the same environment. The runner verifies the authenticated workspace before submission; CPU sandboxes and the GPU service also check placement before allocation. Keep a remote artifact store, registry and image builder accessible to the stack. Connect your submission environment to your ZenML server, select the Modal stack, and check it with `zenml stack describe`.

Build the controller from this checkout so it includes the Modal sandbox settings used here. From the repository root, build a wheel into a clean directory:

```bash
uv build --wheel --out-dir examples/endless_terminals/.local/controller-build
cd examples/endless_terminals
cp Dockerfile.modal .local/controller-build/Dockerfile
```

Build and publish the native dependency image, then use its immutable digest as the Modal controller base. Replace the registry names and digest below. [Dockerfile.modal](Dockerfile.modal) requires exactly one ZenML wheel in its build context and installs it over the native dependency environment.

```bash
docker buildx build --platform linux/amd64 -f Dockerfile.native \
  -t YOUR_REGISTRY/endless-native:latest --push .
docker buildx build --platform linux/amd64 \
  --build-arg BASE_IMAGE=YOUR_REGISTRY/endless-native@sha256:YOUR_DIGEST \
  -t YOUR_REGISTRY/endless-modal:latest --push .local/controller-build
```

Also build and publish [Dockerfile.sandbox](Dockerfile.sandbox) as the CPU helper and the [training server image](training_server/README.md). Install the built ZenML wheel and `modal==1.5.5` in the Python 3.12 submission environment; use [requirements-native.txt](requirements-native.txt) for its training-client dependencies, installing the CPU PyTorch wheel from the index shown in [Dockerfile.native](Dockerfile.native). Install the repository wheel after those dependencies. This is separate from the lighter local evaluator environment below.

Prepare a task bundle using the following section, then copy [modal-training.example.json](modal-training.example.json) to `.local/modal-training.json`. Replace every image placeholder with a published immutable digest. Set `service.workspace` and `sandbox.modal_workspace` to your workspace, and set `service.modal_environment` and `sandbox.modal_environment` to the same environment as both stack components. The training pilot accepts only the DNS task `task_000000_0228cd64`.

```bash
ZENML_ACTIVE_STACK_ID=YOUR_MODAL_STACK_ID python run_modal_training.py \
  --bundle .local/sandbox-bundle --config .local/modal-training.json
```

After a successful registry import, `service.imported_image_id` can reuse that exact Modal image without downloading it again. Set it only after checking the Modal build log maps the image ID to the configured immutable `training_image`; the registry digest remains the source provenance.

The configuration requests one H200, eight CPU cores and 256 GiB host memory for the pinned Qwen2.5-7B model. CPU qualification must establish valid initial grading, a successful reference solution and a failing no-op before the GPU is allocated. The service has a 90-minute deadline including startup. The example attempts one group of eight training episodes, with at most one optimizer update; any equal-reward group produces no update.

Modal rejects volume mounts over nonempty directories. Build [Dockerfile.modal-agent](Dockerfile.modal-agent) with `--build-arg TASK_IMAGE=YOUR_ORIGINAL_TASK_DIGEST` and set `sandbox.modal_agent_image` to its published immutable digest. This derived image empties only `/home/user`; initialization copies that directory from the original task image into the episode Volume, and grading still uses the original image.

Each terminal episode uses a unique Modal Volume for home-directory data, separate seed, agent and reader sandboxes, and a fresh verifier without a volume mount. Task sandboxes block external networking and receive no injected environment values or secrets. Cleanup confirms sandbox termination before removing the episode Volume. The GPU service clears the image’s inherited entrypoint, starts one backend from the uploaded source, and requires that exact process to remain alive during readiness checks. It exposes an authenticated TLS proxy, retains diagnostics and confirms termination during cleanup. Inspect the recorded resource identities after an interrupted controller run.

## Prepare a portable task bundle

Run this from the example directory in the local evaluator environment described below, with Docker running and registry push credentials configured. It downloads the pinned DNS task, builds and qualifies its original image, publishes that image, and records its immutable registry digest. Set `TASK_IMAGE` to a new tag in your own registry. The native pipeline repeats qualification on the remote backend before allocating a GPU.

```bash
export TASK_IMAGE=YOUR_REGISTRY/endless-dns:initial
python - <<'PYTHON'
import json
import os
import subprocess
from pathlib import Path

from dataset import prepare_tasks

bundle = Path(".local/sandbox-bundle")
manifest = prepare_tasks(bundle, ["task_000000_0228cd64"])
task = manifest["tasks"][0]
image = os.environ["TASK_IMAGE"]
subprocess.run(["docker", "tag", task["local_image_id"], image], check=True)
subprocess.run(["docker", "push", image], check=True)
details = json.loads(subprocess.check_output(["docker", "inspect", image]))[0]
repository = image.rsplit(":", 1)[0]
task["image_ref"] = next(
    digest for digest in details["RepoDigests"]
    if digest.startswith(repository + "@sha256:")
)
(bundle / "task-manifest.json").write_text(json.dumps(manifest, indent=2))
PYTHON
```

For Modal, additionally build and publish the derived agent image, using the original `image_ref` from this manifest as `TASK_IMAGE`:

```bash
docker buildx build --platform linux/amd64 -f Dockerfile.modal-agent \
  --build-arg TASK_IMAGE=YOUR_REGISTRY/endless-dns@sha256:YOUR_DIGEST \
  -t YOUR_REGISTRY/endless-dns-agent:initial --push .
```

Set `sandbox.modal_agent_image` to the derived digest and leave the manifest's `image_ref` pointing to the original. Keep the downloaded task files unchanged: the loader verifies their recorded hashes. For baseline screening, prepare each selected task from `tasks.json` in the same bundle, publish each original image, and supply its derived image in `modal_agent_images`. `prepare_tasks` rejects IDs outside the checked-in selection; a larger custom selection requires its own reviewed, hash-pinned manifest.

## Native Kubernetes sandbox pilot

`run_sandbox.py` submits a CPU-only pipeline through ZenML's Kubernetes orchestrator and Kubernetes sandbox component. It uploads a task bundle as a ZenML artifact, runs initial-state qualification plus reference and empty-solution episodes in separate steps, and produces structured evidence and an HTML report. This path was verified on EKS with passing initial/reference checks, a failing no-op, and complete cleanup. A live probe confirmed disabled external networking and no mounted Kubernetes token. This does not train a model.

Build the small CPU helper image with `docker buildx build --platform linux/amd64 -f Dockerfile.sandbox -t YOUR_HELPER_IMAGE .` and publish it to the stack's registry. Set `helper_image` in `sandbox.example.json` to its immutable registry digest. Publish the qualified task image separately and retain its digest as `image_ref` in the task manifest. The uploaded bundle must contain `task-manifest.json` with the pinned `dataset_revision` and selected entry from `tasks.json`, plus that task's directory and original hashed files. The pilot currently accepts one task.

Use a stack containing the existing Kubernetes orchestrator, artifact store, registry and image builder plus a Kubernetes sandbox configured with `incluster=true` in the orchestrator namespace. The controller service account needs the permissions shown in [sandbox-rbac.yaml](sandbox-rbac.yaml). Those permissions apply throughout that namespace, so review them before applying the manifest to a shared cluster. The supplied CPU placement settings select and tolerate `pool=workloads`.

```bash
python run_sandbox.py --bundle ./sandbox-bundle \
  --config sandbox.local.json \
  --service-account endless-terminal-controller
```

Each episode uses a temporary 1 GiB PVC. A trusted seed pod copies the initial home directory, an agent pod modifies it, and a fresh reader exports it after agent termination. A separate verifier pod receives only the audited home archive and trusted tests. Task pods disable non-loopback network interfaces through a trusted init container, omit service-account tokens, and exclude host namespaces. Cleanup records pod identities and volume removal. CPU autoscaling and volume storage may incur costs; GPU capacity is not requested by this pilot.

## Native Kubernetes training pilot

`run_native_training.py` reuses the portable bundle and CPU qualification steps above. After qualification passes, one CPU step creates an internal GPU Job and ClusterIP Service, evaluates the initial adapter, attempts training groups, evaluates the resulting policy, and downloads the final sampling adapter. Terminal episodes and graders still run in separate CPU Kubernetes sandboxes. The GPU pod runs SkyRL on loopback behind a proxy requiring a random per-run API key. The CPU controller uses in-cluster Kubernetes authentication; it does not need local `aws`, `kubectl`, a port forward, or AWS administrator credentials for GPU lifecycle operations.

Build and publish [Dockerfile.native](Dockerfile.native) as the controller image. Its [requirements-native.txt](requirements-native.txt) pins Python 3.12 dependencies, CPU-only PyTorch, and `s3fs==2026.6.0` for compatibility with the pinned Tinker Cookbook dependency set. The Dockerfile installs the CPU PyTorch wheel explicitly and runs `pip check`; use this environment rather than combining the older local training requirements with the native controller. Publish the [training server image](training_server/README.md), helper image, task image and an nginx-unprivileged proxy image separately, and use immutable registry digests for every image.

```bash
docker buildx build --platform linux/amd64 -f Dockerfile.native \
  -t YOUR_CONTROLLER_IMAGE --push .
cp native-training.example.json native-training.local.json
# Replace every image placeholder with its published immutable digest.
python run_native_training.py --bundle ./sandbox-bundle \
  --config native-training.local.json \
  --service-account endless-native-training-controller
```

Use the same Kubernetes stack and namespace as the CPU pilot, with the sandbox configured as `incluster=true`. [native-rbac.yaml](native-rbac.yaml) adds namespaced Service and Secret creation/deletion plus event reads to the CPU sandbox permissions; [sandbox-rbac.yaml](sandbox-rbac.yaml) alone is insufficient. Set both manifest namespaces before applying the native manifest. The GPU pool, device plugin and autoscaler must already support the configured resource request and `pool=gpu` placement. The controller stays on `pool=workloads`.

The supplied configuration selects only `task_000000_0228cd64` and attempts at most two groups of four episodes. Reward remains binary: 1 for an audited pass and 0 for an audited failure. Equal-reward groups skip the optimizer update; two such groups stop this configuration. A completed run with zero optimizer steps demonstrates execution and export, not learning. The controller also stops adding groups when its remaining service budget cannot cover the group, paired evaluation and export.

For response-format experiments, set `training.prompt_variant` to `concise_xml_v1`. This opt-in prompt gives short XML action instructions and a task-independent `pwd` example. The default remains `upstream`, and the parser and grader stay unchanged. Before, training and after episodes use the selected prompt; its variant and SHA-256 are recorded in the comparison protocol. Reports reject comparisons between different prompt protocols.

The native run also publishes an `initial_adapter` artifact exported after the initial evaluation and before any training group. Compare its tensors with `trained_adapter` to verify that an optimizer update changed the saved weights. Failed-run diagnostics retain this initial export when it was completed before the failure.

Successful runs retain `native_training_diagnostics`, including service logs, runtime memory measurements and Kubernetes status evidence. Failures attempt to upload `failed_training_evidence` and `failed_training_diagnostics`. The `trained_adapter` model artifact contains sampling adapter files and provenance hashes, not resumable optimizer state. Inspect the optimizer-step count and paired report before interpreting any score change. The Kubernetes path has completed sampling, export, paired evaluation, and artifact publication on an L4. Its tested groups had equal rewards and therefore no optimizer updates. A fresh Transformers/PEFT process loaded the exported adapter and completed local evaluations, confirming export usability across that backend change. Nonzero-gradient training was verified on the Modal H200 configuration above, not the L4. The paired evaluation uses the current in-memory policy; it does not reload the downloaded artifact.

The Job has a finite startup wait and active deadline. Cleanup collects diagnostics, deletes resources with UID ownership checks, and waits for the owned Job, pods, Service and Secret to disappear. Owner references and a finished-Job TTL provide fallback cleanup after controller loss. None of these checks proves that AWS GPU capacity has returned to zero: the cluster autoscaler retires unused workers, and an external operator must verify the dedicated Auto Scaling group's capacity and EC2 termination after each run. Keep AWS administrator credentials outside the CPU pod.

## Set up the local Docker evaluator

Use Python 3.10–3.14 and a running Docker daemon capable of running `linux/amd64` images. On ARM machines, Docker needs AMD64 emulation. Run commands from this directory:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Connect to your existing ZenML server and select a stack with a **local orchestrator**. The pipeline starts Docker containers on the controller host, so a remote orchestrator is unsupported. Your artifact store can be local or remote, including S3, provided its integration and credentials are configured. Check the active stack with `zenml stack describe`.

The preparation step downloads pinned dataset files, checks their SHA-256 hashes, and builds missing task images. Building images can download base images and packages. Every run performs fresh initial-state, no-op, reference-solution, and corrupted-output qualification in isolated CPU containers. Local caches save downloads and image builds; they do not skip qualification.

## Check the pipeline without inference

```bash
python run.py --mode fixture \
  --data-directory ./data \
  --output-directory ./runs
```

Fixture mode makes no model requests. It supplies each task's reference solution as a scripted command to exercise the evaluation and report path; its results are **not a model score**. Preparation still needs network access when dataset files or build dependencies are missing.

Omit `--task-id` to use all ten reviewed tasks. For a smaller run, repeat the option with IDs from `tasks.json`:

```bash
python run.py --mode fixture \
  --task-id task_000000_009a1afa \
  --task-id task_000000_00e67104
```

## Evaluate an existing endpoint

Provide an OpenAI-compatible API base URL. Include `/v1` when the server requires it; the client appends `/chat/completions`.

```bash
python run.py --mode endpoint \
  --base-url http://127.0.0.1:8000/v1 \
  --model-name Qwen/Qwen2.5-1.5B-Instruct \
  --model-revision 989aa7980e4cf806f80c7fef2b1adb7bc71aa306
```

The model name and revision above are the defaults. Supply the actual immutable model revision when evaluating another checkpoint. For an existing endpoint, that revision is caller-supplied provenance; the client marks it unverified and excludes the run from checkpoint comparisons because it cannot prove which weights the server loaded. Set `ENDLESS_API_KEY` in the environment if authentication is required. Remote endpoints require HTTPS; credentials in URLs and HTTP redirects are rejected.

Endpoint mode does not start or stop the model server. You remain responsible for its lifecycle and any associated GPU capacity. Requests have a subprocess-enforced deadline and no implicit retries.

## Legacy local evaluation with temporary Kubernetes serving

This optional local-controller mode creates a vLLM serving Job in an existing cluster. It does not provision the cluster, namespace, GPU node group, NVIDIA device plugin, or autoscaler. Install and authenticate the external `aws` and `kubectl` CLIs first. This is separate from the native Kubernetes pipeline above.

Use a dedicated GPU Auto Scaling group that starts empty with minimum and desired capacity zero. The cluster autoscaler must be configured to provision a suitable GPU worker for the Job's node selector and resource request. The supplied Job selects `pool=gpu` and tolerates `pool=gpu:NoSchedule`; override `node_selector` and `tolerations` if your dedicated pool uses different labels or taints. The serving image must have a vLLM-compatible entrypoint and be pinned by an immutable image digest. The example pins vLLM 0.10.2.

```bash
cp cloud.example.json cloud.local.json
# Replace every YOUR_* placeholder in cloud.local.json.
python run.py --mode kubernetes --cloud-config-path cloud.local.json
```

The example allows 900 seconds for startup and sets a 3600-second serving Job deadline, including startup. Increase that explicit bound if your selected episode budgets require more time. The evaluator refuses to start an episode without sufficient serving time remaining.

Review the cloud settings before running: this mode can provision billable GPU capacity and terminate the dedicated worker during cleanup. It labels the serving Job with a unique ownership token, uses a local port forward, and records cleanup evidence. Normal completion and handled failures remove the owned Job and verify the GPU group returns to zero capacity and the worker reaches EC2 `terminated`. Cleanup refuses ambiguous ownership or a worker carrying other workloads. Forced termination is disabled in the example configuration.

Controller death, `SIGKILL`, or lost cloud access can prevent cleanup. The Kubernetes Job deadline stops serving but does not itself guarantee the worker is terminated. After an interrupted run, inspect the recorded Job identity and cleanup evidence, then verify the dedicated group's capacity in AWS. Do not share this GPU group with unrelated workloads.

## Legacy local RL pilot

This experimental workflow uses a local controller with remote GPU serving. For the native Kubernetes controller and task runners, use `run_native_training.py` above.

Use Python 3.12 for training and install `requirements-training.txt` in an isolated environment. Build and publish the pinned [SkyRL server image](training_server/README.md) on an AMD64 CPU builder with sufficient disk before allocating a GPU. Set `training_image` in your cloud configuration to the published image digest, and set `server_kind` to `skyrl`. The same dedicated GPU lifecycle requirements apply. The single-GPU configuration targets a 24 GiB NVIDIA GPU; actual memory fit must be checked before a longer run.

```bash
python -m pip install -r requirements-training.txt
cp training.example.json training.local.json
python run_training.py --config training.local.json
```

This local pipeline qualifies tasks in CPU Docker containers, then runs one step that starts remote GPU serving, evaluates the initial adapter, samples training episodes, applies updates, evaluates the resulting policy under the same protocol, downloads the final adapter, and cleans up. A final report step receives the paired evaluation and training artifacts. Keeping these operations within one step avoids passing a live GPU service between independently scheduled steps.

The default is at most 16 groups of four episodes, alternating two simple tasks from the reviewed selection. Reward is exactly 1 for an audited task pass and 0 for an audited failure. Exact sampled token IDs and log probabilities are retained; official Tinker Cookbook code computes group-relative advantages and performs the policy-gradient update. Prompt and terminal-observation tokens do not receive reward advantages. Equal-reward groups produce no optimizer update; four consecutive such groups stop the pilot. A completed pipeline with zero optimizer steps means no learning occurred.

The controller reserves time for the paired evaluation using its full interaction budgets, the observed initial evaluation duration, and an export margin. This is an estimate; the Kubernetes Job deadline remains the hard lifetime bound, and a deadline or infrastructure failure makes the run fail rather than producing a partial success score. Review `serving_deadline` before running and keep the group count small until sampling, updating, and exporting work on the selected GPU.

The `trained_adapter` model artifact contains downloaded sampling adapter weights and file hashes. It is not a resumable optimizer checkpoint. `training_evidence` contains rewards, update metrics, exact sampled tokens, transcripts, and cleanup evidence. The HTML report separates the number of optimizer updates from the before/after task score. These tasks have informed development and are reused for training, so this is a training-set demonstration, not evidence of held-out generalization.

## Inspect and compare artifacts

Open the completed run in ZenML and inspect the HTML report artifact. It shows audited task outcomes, response-format validity, token usage, transcripts, verifier output, and cleanup status. Infrastructure errors remain separate from failed tasks. JSON episode evidence and `report.html` are also written under `<output-directory>/<pipeline-run-id>/`. Failed evaluations retain local evidence and attempt to upload `failed_evaluation_results` and `failed_evaluation_report` before the step fails.

Use the prior **`evaluation_results` artifact version ID**, not its report artifact or pipeline run ID, to compare a later run:

```bash
python run.py --mode kubernetes \
  --cloud-config-path cloud.local.json \
  --baseline-artifact-id YOUR_EVALUATION_ARTIFACT_VERSION_UUID
```

A comparison requires matching task sets, task image and file hashes, dataset revision, evaluation mode, and protocol, including runtime and serving-code hashes. Existing-endpoint runs have unverified model revisions and cannot be compared. Change the model settings explicitly when comparing checkpoints. Paired outcomes from this subset alone do not establish a training gain.

## Runtime boundaries

The local evaluator runs each task in a network-disabled Docker container with one CPU, 1 GiB memory, and a process limit; native pipelines use the Kubernetes or Modal sandbox isolation described above. A persistent Bash process retains working-directory and shell-variable state between commands. Local defaults allow 16 responses, 10 seconds per terminal command, and 180 seconds of agent interaction. Grading has a separate 120-second execution limit; Docker setup and cleanup also have bounded operations.

During model evaluation, the model sees the task instruction and terminal observations. Final graders and reference solutions remain outside the agent container. Fixture mode explicitly executes the reference solution as described above. After interaction, the runner stops task processes and transfers only regular files and directories from `/home/user` into a clean image for grading. Protected-source hashes are checked independently. A raw grader pass counts as an audited pass only when those checks also pass. Tasks requiring changes outside `/home/user` are unsupported. Containers provide process isolation, not protection against Docker or kernel exploits.

The adapter uses Bash pipes and runs the image's Python and pytest directly in the clean verifier. It does not execute the upstream `tests/test.sh` dependency-installation workflow. Scores therefore belong to this recorded adaptation; they should not be presented as canonical Harbor or upstream SkyRL benchmark results. Rebuilt task images may contain newer base packages, so their immutable image IDs are part of the comparison contract.

## Tests and attribution

Inspired by [Mercor and SkyRL's guide to training knowledge-work agents](https://www.mercor.com/blog/training-frontier-knowledge-work-agents-a-397b-rl-training-guide-with-skyrl/), this example demonstrates a smaller workflow using public terminal tasks. It does not reproduce their APEX-Agents training recipe or results.

From this directory, run the focused tests:

```bash
python -m pip install pytest
python -m pytest -q tests runtime/test_runtime.py
```

Dataset files are distributed under the upstream dataset's MIT license. The minimal system prompt and XML action parser are adapted from [Endless Terminals](https://github.com/kanishkg/endless-terminals) at commit `99f4c74b75faacf21e53d3dc01df170902e924cb`, under Apache-2.0; see `runtime/LICENSE.endless-terminals`. The parser intentionally preserves the pinned implementation's last-command selection and done-action precedence.
