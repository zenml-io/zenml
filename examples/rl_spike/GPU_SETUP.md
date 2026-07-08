# GPU setup (Stage 2 — not written yet)

Placeholder. This document gets written in Stage 2 of the spike, after the
dry run is reviewed (STOP GATE 2 in the session plan). It will contain the
exact, docs-grounded instructions for enabling GPU on the AWS Kubernetes
stack:

- GPU node group (instance type + hourly price) and the NVIDIA device
  plugin, with `kubectl` verification commands
- `DockerSettings` / pod resource settings for the GPU steps
  (`generate_rollouts`, `grpo_update`) vs the CPU steps (episode sandboxes)
- the vLLM generation setup per the topology decided at Stage 0 (in-step
  offline batch API; deployer-hosted service documented as the fallback)
- a hand-run smoke sequence (single `nvidia-smi` step → one real episode →
  stop)

Until then: the real (non-`--dry-run`) mode of `run.py` is UNVERIFIED and
should not be attempted.
