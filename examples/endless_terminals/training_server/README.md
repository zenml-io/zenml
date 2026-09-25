# SkyRL training server

This image provides an HTTP training and sampling API on one GPU. In the native pipeline, a CPU ZenML step controls this service and terminal tasks run in separate CPU Kubernetes or Modal sandboxes. The legacy path instead uses a local controller and Docker task containers. The GPU pod needs no Docker daemon and makes no callback to the controller. It runs FSDP training and vLLM inference in alternating phases on the same GPU.

## Build

From the ZenML repository root, on a Linux AMD64 builder with ample disk space:

```bash
docker build --platform linux/amd64 \
  -t endless-training-server:skyrl-0b286ba \
  examples/endless_terminals/training_server
```

The build uses the Dockerfile, entrypoint, backend configuration and `diagnostics.py`. It downloads the pinned SkyRL source archive and verifies its SHA-256 before installing FSDP and Tinker extras with the upstream frozen lock. The source commit is `0b286bacba2bb51dfe50186b6b5d6b1e0b5f5518`. The official base image is pinned by digest in the Dockerfile. The lock resolves Tinker SDK `0.24.0`, PyTorch `2.11.0`, and vLLM `0.28.0`.

FlashAttention and causal-conv1d use the prebuilt CUDA 13/PyTorch 2.11 wheels from the index specified by upstream. The build explicitly forbids compiling those packages. No model weights are downloaded during the image build. A build still needs substantial network and disk capacity: the base image alone contains 7.77 GiB of compressed layers. Allow approximately 60–80 GiB free for base layers, dependency downloads, unpacking, and image snapshots; that planning allowance is an estimate, not a measured completed build size.

## Run in the GPU pod

Use an NVIDIA driver from the r580 series or newer and one GPU. The default model is `Qwen/Qwen2.5-1.5B-Instruct`, pinned to revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`. Override `SKYRL_MODEL_NAME` and `SKYRL_MODEL_REVISION` together for another checkpoint. The entrypoint rejects mutable revisions, downloads that exact snapshot, records `server-identity.json`, creates `/models/base` as a symlink to the snapshot, and passes that stable path to SkyRL. An existing directory at `/models/base` is rejected rather than overwritten. It does not use `trust_remote_code`.

Mount writable storage at `/models` for the model cache and `/checkpoints` for API state and checkpoints. Provide a memory-backed `/dev/shm`, for example 8 GiB, and allow sufficient host RAM for offloaded policy state. The container runs as the base image's `ray` user; volume permissions must allow that user to write. The backend configuration uses one GPU, microbatches of one, gradient checkpointing, an 8192-token context bound, and 35% vLLM GPU utilization. The native Job provides 8 GiB shared memory, requests 26 GiB host memory and limits it to 28 GiB. Set `service.inference_gpu_memory_utilization` to override the inference allocation for a particular native run; its default remains 0.35. The mounted configuration and its hash record the effective value. Larger checkpoints also require sufficient GPU and host memory for the pinned backend’s FP32 training weights; BF16 inference fit does not establish training fit. Sampling has run on a 24 GiB L4 with this configuration; memory fit for a nonzero-gradient optimizer update remains unverified.

The entrypoint starts the API with `uv run --frozen --no-sync --extra fsdp --extra tinker -m skyrl.tinker.api`. SkyRL inspects that parent command to start its background training engine with the same environment flags. Starting the API directly with `python -m skyrl.tinker.api` fails during API startup. `--no-sync` uses the environment installed during the image build without changing dependencies at runtime.

The API listens on **127.0.0.1:8000**. The Kubernetes Job runs an nginx proxy in the same pod, exposes only proxy port 8001 through a ClusterIP Service, and requires a random per-run API key. Modal uses an authenticated proxy on port 8001 through its TLS tunnel. SkyRL remains on loopback. The legacy local-controller path uses `kubectl port-forward` instead. The backend readiness endpoint is:

```text
GET http://127.0.0.1:8000/api/v1/healthz
```

The native controller checks health through the authenticated proxy, then verifies model identity, backend configuration and source hashes through Kubernetes exec. It mounts the current entrypoint, backend configuration and diagnostics from an immutable Secret; those file hashes are recorded in `server-identity.json` and the run evidence. A Kubernetes exec readiness probe can also run the same Python command as the Dockerfile's health check. Docker health checks are not automatically applied by Kubernetes. First startup downloads about 3 GB of model weights and initializes the API; actual model allocation and inference initialization can occur on the first client requests. An HTTP health response alone does not prove a training step fits in GPU memory. Allow at least 15 minutes for the initial download and startup when caches are cold.

The controller should use `tinker==0.24.0`, create one LoRA training client with rank 8, and complete generation before invoking an optimizer step. Use `base_model="/models/base"` when creating the client. `get_server_capabilities()` and `server-identity.json` expose that stable served identity. Load the controller's tokenizer separately using the same Hugging Face model name and revision, since the server's snapshot path is not a local controller path. Configure bounded SDK request timeouts and explicit retry behavior in the controller.

## Export before deleting the pod

SkyRL already exposes sampler checkpoint archives, so no separate file server is needed. Save sampler weights through the SDK and wait for completion:

```python
checkpoint = training_client.save_weights_for_sampler(name="final").result()
print(checkpoint.path)
```

Pinned SkyRL returns a short `tinker://MODEL_ID/CHECKPOINT_ID` identity. The native [checkpoint downloader](../checkpoint_download.py) accepts that form and the canonical `tinker://MODEL_ID/sampler_weights/CHECKPOINT_ID` form, then calls the SDK's explicit `get_checkpoint_archive_url(model_id, checkpoint_id)` method. The SDK's generic Tinker-path helper rejects the short form. Download through the authenticated native proxy, or the same local port forward for legacy use:

```text
GET /api/v1/training_runs/MODEL_ID/checkpoints/CHECKPOINT_ID/download
```

The `/archive` variant returns a redirect to this download route. The native downloader checks that the returned URL belongs to the training origin, authenticates the download, rejects further redirects, and bounds archive size and extraction paths. The controller hashes the extracted files before deleting the Job; ZenML then materializes the local adapter directory into its artifact store. Do not treat the returned `tinker://` URI as durable storage: it identifies server-side state. The server writes sampler archives under `/checkpoints/MODEL_ID/sampler_weights/CHECKPOINT_ID.tar.gz`. Training-state saves are separate from sampler saves; the verified HTTP archive route serves sampler checkpoints only. Preserve a persistent `/checkpoints` volume if resumable optimizer state is required.

The pinned FSDP sampler [routes requests by model ID to the currently loaded vLLM adapter](https://github.com/NovaSky-AI/SkyRL/blob/0b286bacba2bb51dfe50186b6b5d6b1e0b5f5518/skyrl/backends/skyrl_train_backend.py#L1082). Creating a new sampling client with an old sampler URI does not independently reload its saved files. Validate an export by loading its LoRA files into a fresh base model. Record any inference-backend change, such as using Transformers locally instead of SkyRL/vLLM, when interpreting evaluation results.

## Verification and sources

The pinned image has completed native Kubernetes sampling and adapter export on an L4, and nonzero-gradient Qwen2.5-7B LoRA updates on a Modal H200 with 256 GiB host memory. The September 8 DNS demonstration ran 10 initial evaluations, four groups of eight training episodes, and 10 final evaluations. Pass counts were 9/10 before and 10/10 after; two groups updated the optimizer, and two equal-reward groups skipped it. All 392 exported adapter tensors changed and artifact hashes matched. This verifies execution and export, not held-out generalization or a statistically established training gain.

The paired evaluations use the currently loaded policy rather than reloading the downloaded files. A separate fresh Transformers/PEFT process has loaded an earlier exported adapter and completed local task evaluations; that validates export usability across a different inference backend. Native checkpoint downloads retry transient transfer failures and retain redacted failure diagnostics. Final evaluation precedes final export so a transfer failure does not discard the paired evaluation.

- [SkyRL installation and official base images](https://docs.skyrl.ai/docs/getting-started/installation)
- [Pinned dependency and wheel configuration](https://github.com/NovaSky-AI/SkyRL/blob/0b286bacba2bb51dfe50186b6b5d6b1e0b5f5518/pyproject.toml)
- [Pinned Tinker API, including checkpoint download](https://github.com/NovaSky-AI/SkyRL/blob/0b286bacba2bb51dfe50186b6b5d6b1e0b5f5518/skyrl/tinker/api.py)
- [Tinker backend configuration](https://docs.skyrl.ai/docs/tinker/configuration)

The pinned exporter gathers the full state dictionary on CPU even for LoRA, so host memory is a separate constraint from GPU memory. The tested 7B configuration uses an H200 and 256 GiB host RAM; smaller hardware has not been validated for this workload. The initial sampler save permits up to 600 seconds within the remaining service deadline; later saves retain the 180-second default, and sampling-client creation has a separate 60-second timeout. Native export then has a 420-second subprocess deadline.
