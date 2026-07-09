#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""B2b phase 2: TRL-native GRPO over Harbor tasks, inside ONE ZenML step.

The ownership inversion under test (framework_breakout.md Track B, B2b):
TRL owns generation, the multi-turn tool loop, reward collection, and the
optimizer; Harbor owns task + verifier; ZenML owns (a) the step wrapper
with config-in/adapter-out lineage and (b) the sandbox every tool call
executes in (via the vendored bridge — see zenml_sandbox_env.py).

Run from this directory on the `kubernetes_aws` stack (K8s orchestrator +
S3 artifact store + K8s sandbox), with the rl-spike-gpu node group scaled
up (GPU_SETUP.md):

    ../../.venv-b2b/bin/python train_b2b.py            # one bounded run
    ../../.venv-b2b/bin/python train_b2b.py --max-steps 3

Deliberate divergences from the task brief, decided at build time:
- vLLM runs in colocate mode on ONE GPU (each g6.2xlarge node has a
  single L4, so a single trainer pod can never see two GPUs; the brief's
  "needs both GPUs" only applies to the server-mode split, which is out
  of scope for the bounded run).
- The policy is Qwen3-0.6B + fresh LoRA, not the spike's 4B: the bounded
  run proves the mechanism, and 24GB shared between vLLM weights, HF
  weights, and optimizer state is tight enough already.
- No adapter-artifact input for v1: the run starts from a fresh LoRA
  init and emits the trained adapter as the output artifact. Threading a
  previous adapter in is a one-liner once the mechanism is proven.
"""

import argparse
import json
import tempfile
from pathlib import Path
from typing import Annotated, Any, Dict, Tuple, Union

from zenml import pipeline, step
from zenml.config import DockerSettings
from zenml.config.base_settings import BaseSettings
from zenml.integrations.kubernetes.flavors import (
    KubernetesOrchestratorSettings,
)
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings

ECR = "339712793861.dkr.ecr.eu-central-1.amazonaws.com"

# torch + CUDA + vLLM >= 0.22 preinstalled, Ubuntu 24.04 -> Python 3.12
# (Harbor's floor). Same parent the rl_spike pipeline image used.
VLLM_PARENT_IMAGE = "vllm/vllm-openai:v0.24.0-x86_64-ubuntu2404"

DOCKER_SETTINGS = DockerSettings(
    parent_image=VLLM_PARENT_IMAGE,
    apt_packages=["python-is-python3"],
    requirements=[
        # Released zenml: the harbor integration is NOT in it — the
        # vendored zenml_sandbox_env.py in this example covers that.
        "zenml==0.96.1",
        "trl[harbor]==1.7.1",
        "transformers>=5.2.0",
        "peft>=0.17,<1",
        "datasets>=3.0",
        "kubernetes>=21.7,<26",
    ],
    python_package_installer_args={"system": None},
    build_options={"platform": "linux/amd64"},
)

_GPU_TOLERATIONS = [
    {"key": "pool", "operator": "Equal", "value": "gpu", "effect": "NoSchedule"}
]

# The trainer step: one L4 GPU, generous memory. The orchestrator pod also
# pins to the GPU node (no GPU requested) so the ~20GB pipeline image never
# lands on shared CPU nodes (disk-pressure eviction, observed in the RL
# spike).
GPU_STEP_SETTINGS: Dict[str, Union[Dict[str, Any], BaseSettings]] = {
    "orchestrator.kubernetes": KubernetesOrchestratorSettings(
        pod_settings=KubernetesPodSettings(
            node_selectors={"pool": "gpu"},
            tolerations=_GPU_TOLERATIONS,
            resources={
                "requests": {
                    "nvidia.com/gpu": "1",
                    "memory": "16Gi",
                    "cpu": "4",
                },
                "limits": {"nvidia.com/gpu": "1", "memory": "28Gi"},
            },
        )
    ),
}

ORCHESTRATOR_SETTINGS = KubernetesOrchestratorSettings(
    orchestrator_pod_settings=KubernetesPodSettings(
        node_selectors={"pool": "gpu"},
        tolerations=_GPU_TOLERATIONS,
        resources={
            "requests": {"memory": "2Gi", "cpu": "1"},
            "limits": {"memory": "4Gi"},
        },
    ),
    synchronous=False,
)


@step(settings=GPU_STEP_SETTINGS)
def train_grpo(
    model_id: str,
    max_steps: int,
    num_generations: int,
    max_turns: int,
    max_completion_length: int,
) -> Tuple[
    Annotated[Path, "b2b_trained_adapter"],
    Annotated[Dict[str, Any], "b2b_train_metrics"],
]:
    """Run a bounded GRPOTrainer session over the Harbor task suite.

    Everything interesting happens inside `trainer.train()`: TRL generates
    each turn with its colocated vLLM, calls the harness tools (which exec
    into ZenML Sandbox session pods), runs the Harbor verifier for the
    reward, and applies GRPO updates. ZenML sees none of that loop — only
    this step's config in and the adapter + metrics out. That residue IS
    the question (a) evidence.

    Args:
        model_id: HF model id of the policy to train.
        max_steps: Optimizer steps to run (bounded on purpose).
        num_generations: GRPO group size per task prompt.
        max_turns: Tool-calling iterations per rollout (the "3 attempts").
        max_completion_length: Per-turn generation budget in tokens. The
            TRL default (256) clipped 100% of completions on the first
            bounded run — Qwen3's thinking prefix alone exceeds it, so
            the policy never reached a tool call.

    Returns:
        The trained LoRA adapter directory and a metrics dict.
    """
    from peft import LoraConfig
    from trl import GRPOConfig, GRPOTrainer
    from trl.experimental.harbor import HarborSpec

    from zenml_harness import ZenMLPipelineEnv

    spec = HarborSpec(
        str(Path(__file__).parent),
        agent=ZenMLPipelineEnv,
    )

    output_dir = Path(tempfile.mkdtemp(prefix="b2b_grpo_"))
    args = GRPOConfig(
        output_dir=str(output_dir / "checkpoints"),
        max_steps=max_steps,
        num_generations=num_generations,
        per_device_train_batch_size=num_generations,
        gradient_accumulation_steps=1,
        learning_rate=1e-5,
        max_tool_calling_iterations=max_turns,
        max_completion_length=max_completion_length,
        use_vllm=True,
        vllm_mode="colocate",
        # 24GB L4 shared between vLLM and the training pass: without a
        # cap, vLLM's default share left too little headroom and step 2's
        # backward OOMed (run 068c4343, 2026-07-09). Checkpointing trades
        # compute for the multi-turn sequences' activation memory.
        vllm_gpu_memory_utilization=0.25,
        # At 0.25 the default max seq len (40960 for Qwen3) no longer
        # fits the KV cache (run 9f7bca1a); 8192 covers prompt + 3 turns
        # of 2048-token completions. Sleep mode offloads vLLM weights
        # during the training pass — the other half of the OOM fix.
        vllm_max_model_length=8192,
        vllm_enable_sleep_mode=True,
        gradient_checkpointing=True,
        log_completions=True,
        logging_steps=1,
        save_strategy="no",
        report_to="none",
        bf16=True,
    )
    trainer = GRPOTrainer(
        model=model_id,
        args=args,
        train_dataset=spec.train_dataset,
        environment_factory=spec.environment_factory,
        reward_funcs=spec.reward_funcs,
        peft_config=LoraConfig(
            r=16,
            lora_alpha=32,
            target_modules="all-linear",
            task_type="CAUSAL_LM",
        ),
    )
    result = trainer.train()

    adapter_dir = output_dir / "adapter"
    trainer.save_model(str(adapter_dir))

    metrics: Dict[str, Any] = dict(result.metrics or {})
    metrics["log_history"] = trainer.state.log_history
    metrics["model_id"] = model_id
    metrics["max_steps"] = max_steps
    metrics["num_generations"] = num_generations
    print("training metrics:", json.dumps(metrics, default=str)[:2000])
    return adapter_dir, metrics


@pipeline(
    settings={
        "docker": DOCKER_SETTINGS,
        "orchestrator.kubernetes": ORCHESTRATOR_SETTINGS,
    },
    enable_cache=False,
)
def b2b_trl_harbor_training(
    model_id: str = "Qwen/Qwen3-0.6B",
    max_steps: int = 2,
    num_generations: int = 4,
    max_turns: int = 3,
    max_completion_length: int = 2048,
) -> None:
    """One bounded TRL-drives-Harbor training run on ZenML."""
    train_grpo(
        model_id=model_id,
        max_steps=max_steps,
        num_generations=num_generations,
        max_turns=max_turns,
        max_completion_length=max_completion_length,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen3-0.6B")
    parser.add_argument("--max-steps", type=int, default=2)
    parser.add_argument("--num-generations", type=int, default=4)
    parser.add_argument("--max-turns", type=int, default=3)
    parser.add_argument("--max-completion-length", type=int, default=2048)
    args = parser.parse_args()
    b2b_trl_harbor_training(
        model_id=args.model,
        max_steps=args.max_steps,
        num_generations=args.num_generations,
        max_turns=args.max_turns,
        max_completion_length=args.max_completion_length,
    )
