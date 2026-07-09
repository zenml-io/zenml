# B2b — TRL drives Harbor, ZenML Sandbox underneath

Spike code for task B2b (`framework_breakout.md` Track B): TRL's
`GRPOTrainer(environment_factory=...)` owns generation, the multi-turn
tool loop, reward, and training; Harbor owns task + verifier; **the
sandbox every tool call executes in is a ZenML Sandbox session**. Findings
live in `B2B_FINDINGS.md`; branch `spike/b2b-trl-harbor` merges nowhere.

```
GRPOTrainer (TRL v1, vLLM colocate — holds policy tokens/logprobs)
  -> ZenMLPipelineEnv (zenml_harness.py: HarborEnv subclass, 2 tools)
    -> Harbor EnvironmentFactory (via TrialEnvironmentConfig.import_path)
      -> ZenMLSandboxEnvironment (zenml_sandbox_env.py, vendored bridge)
        -> Client().active_stack.sandbox.create_session()  (K8s pods)
```

## Files

- `tasks/` — the rl_spike pipeline-writing task recast as 3 multi-turn
  Harbor tasks (write `/app/pipeline.py`; may execute + fix; 3 turns).
  The verifier is the spike's `score_pipeline.py` verbatim, adapted to
  Harbor's reward contract by `tests/test.sh`.
- `zenml_harness.py` — the TRL harness (`write_pipeline` /
  `run_pipeline` tools). Its `_start` override carries the whole
  TRL-side gap: TRL only exposes Harbor's environment `type` enum, not
  `import_path`.
- `zenml_sandbox_env.py` — the ZenML bridge, vendored (the remote image
  installs released zenml, which lacks the unmerged harbor integration).
- `smoke_env.py` — phase-1 smoke: drive the harness by hand (no
  GPU/vLLM). `--fix-loop` plays broken → traceback → fixed.
- `train_b2b.py` — phase 2: one ZenML step running a bounded
  `GRPOTrainer` session on the `kubernetes_aws` stack (S3 artifact
  store), GPU node group per `../rl_spike/GPU_SETUP.md`.

## Running

```bash
# once: venv per requirements.txt header; then, in this directory:
../../.venv-b2b/bin/zenml init && ../../.venv-b2b/bin/zenml project set rl-spike

# phase 1 (laptop, K8s sandbox pods on staging):
../../.venv-b2b/bin/zenml stack set rl-spike-harbor-k8s
../../.venv-b2b/bin/python smoke_env.py [--fix-loop]

# phase 2 (scale rl-spike-gpu up first; scale to 0 after!):
../../.venv-b2b/bin/zenml stack set kubernetes_aws
../../.venv-b2b/bin/python train_b2b.py --max-steps 2
```
