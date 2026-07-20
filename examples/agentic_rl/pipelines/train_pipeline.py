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
"""Tier 1: gate -> prime-rl trainer (one command step) -> receipts.

The trainer is deliberately ONE opaque step. prime-rl owns the RL loop
(three cooperating processes, TOML-driven); mapping its internals onto
ZenML steps was tried and rejected in the RL spike as a mid-run-growing
DAG. One step is not one record, though: `ingest_rollout_traces` turns
the trainer's per-rollout traces.jsonl into a table with one row per
rollout, and the report walks reward -> sandbox/runtime id ->
checkpoint.
"""

from typing import Any, Dict  # noqa: F401

from steps.checkpoint import find_checkpoint
from steps.ingest_rollout_traces import ingest_rollout_traces
from steps.lineage_report import build_lineage_report
from steps.preflight import preflight_sandbox
from steps.serve import (
    probe_policy_service,
    serve_checkpoint,
    stop_policy_service,
)

from zenml import pipeline
from zenml.steps import CommandStep


@pipeline(dynamic=True)
def agentic_rl_train(
    preflight_image: str = "zenml-rl-scorer:0.1",
    prime_rl_dir: str = "",
    rl_config: str = "configs/rl.toml",
    output_dir: str = "prime-rl-output",
    expected_min_rollouts: int = 1,
    after_eval: bool = False,
    serve_image: str = "vllm/vllm-openai:latest",
) -> None:
    """Gate on a cheap eval campaign, then train and ingest the receipts.

    Dynamic-pipeline calls are synchronous, so ordering is the body
    order: if the gate raises, the trainer command step never launches
    and the GPU is never billed for a doomed run. Caching: the gate
    campaign shards cache (reruns are free); the trainer is a
    ``CommandStep`` (uncacheable by contract) and ingest/checkpoint
    steps opt out explicitly because their inputs (a path string) do
    not capture the world they read.

    Args:
        preflight_image: The scorer image rollouts run on; validated
            in a sandbox session before the trainer launches.
        prime_rl_dir: Path to a prime-rl checkout (its uv project).
            The trainer shells out to it — prime-rl is git-only and
            owns its own environment.
        rl_config: prime-rl TOML config path, resolved by prime-rl.
        output_dir: prime-rl ``--output-dir``. Must be storage that
            this pipeline's later steps can read (shared storage on
            multi-machine stacks).
        expected_min_rollouts: Ingest fails below this rollout count.
        after_eval: Opt in to the after-eval leg — serve the trained
            checkpoint as a run-scoped service, probe it, and stop it.
            Off by default because it provisions a GPU serving pod.
        serve_image: The serving container image for the after-eval leg
            (a vLLM image).
    """
    # One sandbox session on the pinned image proves the reward
    # substrate works; if it raises, the GPU is never billed.
    verdict = preflight_sandbox(image=preflight_image)

    # The trainer: one opaque command step. `uv run --project` uses the
    # prime-rl checkout's own environment (Python 3.12, torch, vllm)
    # instead of this example's venv — the two are deliberately
    # separate worlds, connected only by files under output_dir.
    train_prime_rl = CommandStep(
        command=[
            "uv",
            "run",
            "--project",
            prime_rl_dir,
            "rl",
            "@",
            rl_config,
            "--output-dir",
            output_dir,
            "--ckpt",
        ],
        name="train_prime_rl",
    )
    train_prime_rl()

    rollout_table = ingest_rollout_traces(
        output_dir=output_dir,
        expected_min_rollouts=expected_min_rollouts,
    )
    checkpoint_dir = find_checkpoint(output_dir=output_dir)
    build_lineage_report(
        rollout_table=rollout_table,
        gate_verdict=verdict,
        checkpoint_dir=checkpoint_dir,
    )

    # The after-eval leg: serve -> probe -> stop. The full "Harbor
    # agents evaluate the served policy" campaign is deliberately cut
    # (it needs an endpoint-calling Harbor agent plus sandbox egress,
    # neither of which exists yet). The probe stands in: it proves the
    # service lifecycle and the checkpoint->service lineage join end to
    # end, from the step rather than from a sandbox. stop is ordered
    # after probe explicitly — both only consume the service artifact,
    # so without the edge they would be unordered.
    if after_eval:
        # Stands up a GPU serving pod (KubernetesPodService) running
        # vLLM on the trained checkpoint; the returned handle is a
        # lineage artifact. Lifecycle lives in steps/serve.py; the
        # teardown guarantee is the pod's max-lifetime deadline.
        service = serve_checkpoint(
            checkpoint_dir=checkpoint_dir, image=serve_image
        )
        probe_policy_service(service=service)
        stop_policy_service(service=service, after="probe_policy_service")
