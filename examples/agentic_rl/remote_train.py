"""Temporary driver: split-shape train tier on the kubernetes_aws stack."""

import sys
from pathlib import Path

EXAMPLE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EXAMPLE_DIR))

from typing import Annotated  # noqa: E402

from steps.collect_rollout_steps import collect_rollout_steps  # noqa: E402
from steps.lineage_report import build_lineage_report  # noqa: E402
from steps.preflight import preflight_sandbox  # noqa: E402
from steps.serve import stop_policy_service  # noqa: E402

from zenml import pipeline, step  # noqa: E402
from zenml.config import DockerSettings  # noqa: E402
from zenml.enums import StepRuntime  # noqa: E402
from zenml.execution.pipeline.dynamic.run_context import (  # noqa: E402
    DynamicPipelineRunContext,
)
from zenml.integrations.kubernetes.flavors import (  # noqa: E402
    KubernetesOrchestratorSettings,
)
from zenml.integrations.kubernetes.pod_settings import (  # noqa: E402
    KubernetesPodSettings,
)
from zenml.services import BaseService  # noqa: E402
from zenml.services.service_status import ServiceState  # noqa: E402
from zenml.steps import CommandStep  # noqa: E402

ECR = "339712793861.dkr.ecr.eu-central-1.amazonaws.com"
TRAINER_IMAGE = f"{ECR}/zenml-agentic-rl-trainer:0.1"
SCORER_IMAGE = f"{ECR}/zenml-rl-scorer:0.1"

# The rl launcher rebuilds the per-process weight_broadcast configs from
# the shared block and hard-codes host="localhost", which breaks when the
# inference server is on another node. Bypass: let a dry run write the
# resolved subconfigs, patch the NCCL host to the pod IP, then launch the
# orchestrator and trainer directly, the way prime-rl multi-node
# deployments do.
TRAIN_COMMAND = """
set -e
# Isolated command steps run the raw command in a fresh pod without the
# code checkout the runner pod gets, so pull the snapshot's code archive
# the way the step entrypoint does before touching any repo files.
python - <<'CODEEOF'
import os
from uuid import UUID

from zenml.client import Client
from zenml.utils import code_utils

client = Client()
run = client.get_pipeline_run(UUID(os.environ["ZENML_PIPELINE_RUN_ID"]))
snapshot = run.snapshot
if snapshot is None or snapshot.code_path is None:
    raise RuntimeError("The run's snapshot has no code archive to download.")
code_utils.download_code_from_artifact_store(
    code_path=snapshot.code_path,
    artifact_store=client.active_stack.artifact_store,
)
CODEEOF
cd code
uv pip install --python /app/.venv/bin/python ./verifiers_env
export ZENML_VERIFIERS_RUNTIME=1
export TRAINER_HOST="$(hostname -i)"
sed "s/__TRAINER_HOST__/$TRAINER_HOST/" configs/rl-split.toml > /tmp/rl-split.toml
uv run --project /app rl @ /tmp/rl-split.toml --output-dir prime-rl-output --ckpt --dry-run
uv run --project /app python - prime-rl-output/configs/orchestrator.toml prime-rl-output/configs/trainer.toml <<'EOF'
import os
import sys
import tomllib

import tomli_w

for path in sys.argv[1:]:
    with open(path, "rb") as f:
        cfg = tomllib.load(f)
    broadcast = cfg.get("weight_broadcast")
    if isinstance(broadcast, dict) and broadcast.get("type") == "nccl":
        broadcast["host"] = os.environ["TRAINER_HOST"]
        with open(path, "wb") as f:
            tomli_w.dump(cfg, f)
        print("patched nccl host in", path)
EOF
mkdir -p prime-rl-output/logs/trainer/torchrun
set +e
uv run --project /app orchestrator @ prime-rl-output/configs/orchestrator.toml > prime-rl-output/logs/orchestrator.log 2>&1 &
ORCH=$!
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True uv run --project /app torchrun --role=trainer --rdzv-endpoint=localhost:29400 --nproc-per-node=1 --log-dir=prime-rl-output/logs/trainer/torchrun --redirect=3 --tee=3 -m prime_rl.trainer.rl.train @ prime-rl-output/configs/trainer.toml > prime-rl-output/logs/trainer.log 2>&1 &
TRAIN=$!
wait $ORCH
ORCH_CODE=$?
echo "orchestrator exited with $ORCH_CODE"
if [ $ORCH_CODE -ne 0 ]; then kill $TRAIN 2>/dev/null; fi
wait $TRAIN
TRAIN_CODE=$?
echo "trainer exited with $TRAIN_CODE"
echo "=== orchestrator.log tail ==="
tail -40 prime-rl-output/logs/orchestrator.log
echo "=== trainer.log tail ==="
tail -40 prime-rl-output/logs/trainer.log
[ $ORCH_CODE -eq 0 ] && [ $TRAIN_CODE -eq 0 ]
"""


@step(enable_cache=False)
def start_inference_service(
    image: str,
    port: int = 8000,
) -> Annotated[BaseService, "inference_service"]:
    """Start the prime-rl inference server as a named pod service.

    Args:
        image: The trainer image (contains prime-rl and its env).
        port: The port the inference server listens on.

    Raises:
        RuntimeError: If the service does not become ACTIVE in time.

    Returns:
        The running inference service.
    """
    from zenml.client import Client
    from zenml.integrations.kubernetes.services import (
        KubernetesPodService,
        KubernetesPodServiceConfig,
    )

    config = KubernetesPodServiceConfig(
        name="prime-infer",
        image=image,
        command=[
            "bash",
            "-lc",
            "uv run --project /app inference --weight-broadcast.type nccl",
        ],
        env={"WANDB_MODE": "disabled"},
        namespace="michael",
        port=port,
        gpu_count=1,
        cpu_request="4",
        memory_request="16Gi",
        max_lifetime_seconds=7200,
        pod_settings=KubernetesPodSettings(
            node_selectors={"pool": "gpu"},
            tolerations=[
                {"key": "pool", "value": "gpu", "effect": "NoSchedule"}
            ],
        ),
    )
    client = Client()
    stale = client.list_services(
        project=client.active_project.id,
        service_name=config.service_name,
    )
    for item in stale.items:
        client.delete_service(item.id)
    response = client.create_service(
        config=config, service_type=KubernetesPodService.SERVICE_TYPE
    )
    service = KubernetesPodService(uuid=response.id, config=config)
    service.start(timeout=0)
    # KubernetesPodService.provision builds a monitor-less endpoint and
    # never sets its admin_state, so is_running stays False forever and
    # start() polls to the full timeout. Align the endpoint admin state
    # before polling.
    if service.endpoint:
        service.endpoint.admin_state = ServiceState.ACTIVE
    if not service.poll_service_status(timeout=1500):
        raise RuntimeError(
            f"Inference service did not become ACTIVE.\n"
            f"{service.get_service_status_message()}"
        )
    Client().update_service(
        id=response.id,
        name=config.service_name,
        service_source=service.model_dump().get("type"),
        admin_state=service.admin_state,
        status=service.status.model_dump(),
        endpoint=service.endpoint.model_dump() if service.endpoint else None,
    )
    return service


@pipeline(dynamic=True, enable_cache=False)
def agentic_rl_train_split() -> None:
    """Split-shape train: external inference, isolated 1 GPU trainer, bookends."""
    run_context = DynamicPipelineRunContext.get()
    assert run_context

    verdict = preflight_sandbox(image=SCORER_IMAGE)
    service = start_inference_service(image=TRAINER_IMAGE)
    try:
        train_prime_rl = CommandStep(
            command=["bash", "-lc", TRAIN_COMMAND],
            name="train_prime_rl",
            runtime=StepRuntime.ISOLATED,
            environment={
                "WANDB_MODE": "disabled",
                # Consumed by the code download in the train command and
                # by the rollout step tracking in the verifiers env
                # package.
                "ZENML_PIPELINE_RUN_ID": str(run_context.run.id),
                "ZENML_ROLLOUT_UPSTREAM_STEP": "train_prime_rl",
            },
            settings={"orchestrator.kubernetes": trainer_k8s_settings},
        )
        train_prime_rl()

        # The trainer pod's filesystem is gone once the isolated step
        # finishes, so the rollout record is read back from the tracked
        # rollout step runs instead of traces.jsonl, and no checkpoint
        # directory is registered.
        rollout_table = collect_rollout_steps(expected_min_rollouts=1)
        build_lineage_report(
            rollout_table=rollout_table,
            gate_verdict=verdict,
            lineage_tier="step (rollout step runs and metadata)",
        )
    finally:
        stop_policy_service(service=service)


docker_settings = DockerSettings(
    parent_image=TRAINER_IMAGE,
    skip_build=True,
)

# The trainer runs as an isolated step in its own GPU pod, so the
# orchestrator pod only hosts the runner and the bookend steps.
k8s_settings = KubernetesOrchestratorSettings(
    orchestrator_pod_settings=KubernetesPodSettings(
        resources={
            "requests": {"cpu": "2", "memory": "6Gi"},
            "limits": {"memory": "8Gi"},
        },
    ),
)

trainer_k8s_settings = KubernetesOrchestratorSettings(
    pod_settings=KubernetesPodSettings(
        node_selectors={"pool": "gpu"},
        tolerations=[{"key": "pool", "value": "gpu", "effect": "NoSchedule"}],
        resources={
            "requests": {
                "cpu": "6",
                "memory": "20Gi",
                "nvidia.com/gpu": "1",
            },
            "limits": {"memory": "26Gi", "nvidia.com/gpu": "1"},
        },
    ),
)

agentic_rl_train_split.with_options(
    settings={
        "docker": docker_settings,
        "orchestrator.kubernetes": k8s_settings,
    }
)()
