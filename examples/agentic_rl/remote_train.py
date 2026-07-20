"""Temporary driver: split-shape train tier on the kubernetes_aws stack."""

import sys
from pathlib import Path

EXAMPLE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EXAMPLE_DIR))

from typing import Annotated  # noqa: E402
from uuid import uuid4  # noqa: E402

from steps.checkpoint import find_checkpoint  # noqa: E402
from steps.ingest_rollout_traces import ingest_rollout_traces  # noqa: E402
from steps.lineage_report import build_lineage_report  # noqa: E402
from steps.preflight import preflight_sandbox  # noqa: E402
from steps.serve import stop_policy_service  # noqa: E402

from zenml import pipeline, step  # noqa: E402
from zenml.config import DockerSettings  # noqa: E402
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
    """Split-shape train: external inference, 1 GPU trainer, bookends."""
    verdict = preflight_sandbox(image=SCORER_IMAGE)
    service = start_inference_service(image=TRAINER_IMAGE)
    try:
        train_prime_rl = CommandStep(
            command=["bash", "-lc", TRAIN_COMMAND],
            name="train_prime_rl",
        )
        train_prime_rl()

        rollout_table = ingest_rollout_traces(
            output_dir="prime-rl-output",
            expected_min_rollouts=1,
        )
        checkpoint_dir = find_checkpoint(output_dir="prime-rl-output")
        build_lineage_report(
            rollout_table=rollout_table,
            gate_verdict=verdict,
            checkpoint_dir=checkpoint_dir,
        )
    finally:
        stop_policy_service(service=service)


docker_settings = DockerSettings(
    parent_image=TRAINER_IMAGE,
    skip_build=True,
)

k8s_settings = KubernetesOrchestratorSettings(
    orchestrator_pod_settings=KubernetesPodSettings(
        node_selectors={"pool": "gpu"},
        tolerations=[
            {"key": "pool", "value": "gpu", "effect": "NoSchedule"}
        ],
        resources={
            "requests": {
                "cpu": "6",
                "memory": "20Gi",
                "nvidia.com/gpu": "1",
            },
            "limits": {"memory": "26Gi", "nvidia.com/gpu": "1"},
        },
        env=[{"name": "WANDB_MODE", "value": "disabled"}],
    ),
)

agentic_rl_train_split.with_options(
    settings={
        "docker": docker_settings,
        "orchestrator.kubernetes": k8s_settings,
    }
)()
