"""Steps for the disaggregated RL loop: one trainer, many generators."""

import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional

from async_scoring import score_group
from async_shared import (
    claim_groups,
    discard_group,
    enqueue_group,
    gc_retired,
    get_current,
    get_endpoint,
    init_run_dir,
    is_live,
    live_versions,
    mark_retired,
    publish_version,
    set_endpoint,
    stage_adapter_in,
    stage_adapter_out,
)
from async_training import run_grpo_step
from generation import RemoteVLLMGenerator, get_generator
from remote_settings import SANDBOX_SETTINGS
from serving.vllm_http import VLLMEndpointError

from zenml import log_metadata, step


def _deploy_version(
    run_dir: str,
    version: int,
    adapter_dir: str,
    model_name: str,
    deploy_config: Dict[str, Any],
) -> None:
    """Serve a version's adapter and record its endpoint.

    Kubernetes gives the version its own deployment; Modal loads it as a
    LoRA into the one shared app. Both record the same endpoint shape.

    Args:
        run_dir: The shared run directory.
        version: Version number to serve.
        adapter_dir: Local adapter directory to push into the server.
        model_name: HF model ID of the policy base model.
        deploy_config: Remote-serving deployment settings.
    """
    adapter_name = f"v{version}"
    if deploy_config.get("backend") == "modal":
        from serving.modal_vllm import (
            ensure_modal_deployment,
            load_lora_adapter_modal,
        )

        endpoint = ensure_modal_deployment(
            model_name=model_name, deploy_config=deploy_config
        )
        load_lora_adapter_modal(
            endpoint=endpoint,
            adapter_dir=adapter_dir,
            adapter_name=adapter_name,
            deploy_config=deploy_config,
        )
    else:
        from serving import ensure_vllm_deployment, load_lora_adapter

        endpoint = ensure_vllm_deployment(
            model_name=model_name,
            image=deploy_config["image"],
            namespace=deploy_config["namespace"],
            deployment_name=f"{deploy_config['deployment_prefix']}-v{version}",
            service_name=f"{deploy_config['service_prefix']}-v{version}",
            max_lora_rank=deploy_config["max_lora_rank"],
            service_account_name=deploy_config["service_account_name"],
        )
        load_lora_adapter(
            endpoint=endpoint,
            adapter_dir=adapter_dir,
            adapter_name=adapter_name,
        )
    set_endpoint(
        run_dir,
        version,
        {
            **endpoint,
            "adapter_name": adapter_name,
            "backend": deploy_config.get("backend", "k8s"),
        },
    )


def _teardown_version(run_dir: str, version: int) -> None:
    """Retire a version's serving: delete its deployment or unload its LoRA.

    Args:
        run_dir: The shared run directory.
        version: Version number to spin down.
    """
    endpoint = get_endpoint(run_dir, version)
    if endpoint is None:
        return
    if endpoint.get("backend") == "modal":
        from serving.modal_vllm import unload_lora_adapter_modal

        unload_lora_adapter_modal(
            endpoint=endpoint, adapter_name=endpoint["adapter_name"]
        )
    else:
        from serving import delete_vllm_deployment

        delete_vllm_deployment(endpoint=endpoint)


@step
def publish_initial_version(
    run_dir: str,
    adapter: Path,
    model_name: str,
    serving_mode: str = "local",
    deploy_config: Optional[Dict[str, Any]] = None,
) -> None:
    """Bootstrap the run: stage the init adapter as version 0.

    In remote mode, also deploy version 0's vLLM server and load the
    adapter into it before publishing.

    Args:
        run_dir: The shared run directory.
        adapter: The initial LoRA adapter directory from init_lora.
        model_name: HF model ID of the policy base model.
        serving_mode: "local" runs vLLM in the generator; "remote" serves
            each version from its own vLLM deployment.
        deploy_config: Remote-serving deployment settings (remote only).
    """
    init_run_dir(run_dir)
    stage_adapter_in(str(adapter), run_dir, 0)
    if serving_mode == "remote":
        assert deploy_config is not None
        _deploy_version(run_dir, 0, str(adapter), model_name, deploy_config)
    publish_version(run_dir, 0)


@step
def teardown_serving(run_dir: str, serving_mode: str = "local") -> None:
    """Tear down any still-live version's serving at the end of a run.

    Args:
        run_dir: The shared run directory.
        serving_mode: "local" is a no-op; "remote" tears down live versions.
    """
    if serving_mode != "remote":
        return
    for version in live_versions(run_dir):
        mark_retired(run_dir, version)
        _teardown_version(run_dir, version)


@step
def train_step(
    run_dir: str,
    model_name: str,
    group_size: int,
    groups_per_step: int,
    learning_rate: float,
    max_versions: int,
    poll_interval_seconds: float,
    idle_timeout_seconds: float,
    gc_grace_seconds: float,
    serving_mode: str = "local",
    deploy_config: Optional[Dict[str, Any]] = None,
) -> int:
    """Run one GRPO step: claim rollouts, train, publish, retire the oldest.

    Waits for fresh rollouts to appear, trains one version from them,
    publishes it, and retires versions past the staleness window.

    Args:
        run_dir: The shared run directory.
        model_name: HF model ID of the policy base model.
        group_size: GRPO group size.
        groups_per_step: Target number of task-groups for this step.
        learning_rate: Optimizer learning rate.
        max_versions: Staleness window; rollouts older than this are
            dropped and versions this far back are retired.
        poll_interval_seconds: Sleep between queue polls while waiting.
        idle_timeout_seconds: Give up waiting for rollouts after this long.
        gc_grace_seconds: Grace before deleting a retired adapter.
        serving_mode: "local" runs vLLM in the generator; "remote" serves
            each version from its own vLLM deployment.
        deploy_config: Remote-serving deployment settings (remote only).

    Raises:
        RuntimeError: If no rollouts arrive within idle_timeout_seconds.

    Returns:
        The version produced by this step.
    """
    waited = 0.0
    while True:
        current = get_current(run_dir)
        min_version = current - max_versions + 1
        result = claim_groups(
            run_dir, max_groups=groups_per_step, min_version=min_version
        )
        if result.groups:
            break
        if waited >= idle_timeout_seconds:
            raise RuntimeError(
                f"No rollouts within {idle_timeout_seconds:.0f}s "
                f"(queue below v{min_version})."
            )
        print(
            f"[trainer] waiting for rollouts >= v{min_version} "
            f"(current=v{current}, waited {waited:.0f}/"
            f"{idle_timeout_seconds:.0f}s, dropped_stale={result.dropped_stale})"
        )
        time.sleep(poll_interval_seconds)
        waited += poll_interval_seconds

    # Keep the freshest group per task; a GRPO batch needs distinct
    # prompts, and duplicate tasks are staler by construction.
    deduped: Dict[str, Any] = {}
    dropped_dup = 0
    consumed = []
    for group in result.groups:
        consumed.append(group.path)
        key = group.episodes[0]["prompt_text"]
        if key in deduped:
            dropped_dup += 1
            continue
        deduped[key] = group
    groups = list(deduped.values())
    episodes = [e for group in groups for e in group.episodes]
    staleness = [current - group.version for group in groups]

    new_version = current + 1
    base_local = stage_adapter_out(run_dir, current)
    out_local = os.path.join(
        tempfile.mkdtemp(prefix="async-rl-out-"), "adapter"
    )
    try:
        metrics = run_grpo_step(
            episodes=episodes,
            base_adapter_dir=Path(base_local),
            out_adapter_dir=Path(out_local),
            model_name=model_name,
            group_size=group_size,
            learning_rate=learning_rate,
        )
        stage_adapter_in(out_local, run_dir, new_version)
        if serving_mode == "remote":
            assert deploy_config is not None
            _deploy_version(
                run_dir, new_version, out_local, model_name, deploy_config
            )
    finally:
        shutil.rmtree(base_local, ignore_errors=True)
        shutil.rmtree(os.path.dirname(out_local), ignore_errors=True)
    publish_version(run_dir, new_version)

    keep_from = new_version - max_versions + 1
    for version in live_versions(run_dir):
        if version < keep_from:
            # Drop LIVE before deleting the deployment so a generator that
            # fails against the torn-down server sees a not-live version and
            # reports it cleanly rather than as an infra error.
            mark_retired(run_dir, version)
            if serving_mode == "remote":
                _teardown_version(run_dir, version)
    gc_retired(run_dir, gc_grace_seconds)

    for path in consumed:
        discard_group(path)

    mean_staleness = round(sum(staleness) / len(staleness), 2)
    print(
        f"[trainer] v{new_version} groups={len(groups)} "
        f"stale~{mean_staleness} reward={metrics['mean_reward']}"
    )
    log_metadata(
        metadata={
            "trained_version": new_version,
            "base_version": current,
            "groups_trained": len(groups),
            "dropped_stale": result.dropped_stale,
            "dropped_duplicate": dropped_dup,
            "mean_staleness": mean_staleness,
            "max_staleness": max(staleness),
            **metrics,
        }
    )
    return new_version


@step(settings=SANDBOX_SETTINGS)
def generate_and_enqueue(
    run_dir: str,
    task: Dict[str, Any],
    model_name: str,
    group_size: int,
    dry_run: bool,
    temperature: float,
    max_tokens: int,
    serving_mode: str = "local",
) -> None:
    """Generate one group against the current version, score it, enqueue it.

    Never raises. Aborts gracefully if the target version is retired
    before the group is enqueued, so a version shutdown mid-generation
    does not crash the rollout pipeline. In remote mode a version whose
    server was already torn down is reported as a clear "version_retired"
    skip, and the rollout loop retries against the new current version.

    Args:
        run_dir: The shared run directory.
        task: The task record to generate a group for.
        model_name: HF model ID of the policy base model.
        group_size: Completions per task (GRPO group size).
        dry_run: True selects the stub generator (CPU, local only).
        temperature: Sampling temperature (vLLM path).
        max_tokens: Generation cap per completion (vLLM path).
        serving_mode: "local" loads the adapter from disk and runs vLLM in
            the generator; "remote" calls the version's vLLM endpoint.
    """
    info: Dict[str, Any] = {"task_id": task.get("id", "?")}
    local_adapter = None
    try:
        version = get_current(run_dir)
        if version is None:
            info["skipped"] = "no_version"
        elif not is_live(run_dir, version):
            info["skipped"] = "version_not_live"
        else:
            raw_episodes = None
            if serving_mode == "remote":
                endpoint = get_endpoint(run_dir, version)
                if endpoint is None:
                    info["skipped"] = "no_endpoint"
                else:
                    generator = RemoteVLLMGenerator(
                        endpoint_url=endpoint["url"],
                        adapter_name=endpoint["adapter_name"],
                        model_name=model_name,
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )
                    try:
                        raw_episodes = generator.generate([task], group_size)
                    except VLLMEndpointError as e:
                        # The server was torn down after we read the LIVE
                        # marker. Report it clearly and let the rollout loop
                        # retry against the new current version.
                        if is_live(run_dir, version):
                            raise
                        info["skipped"] = "version_retired"
                        info["version"] = version
                        info["detail"] = str(e)
            else:
                local_adapter = stage_adapter_out(run_dir, version)
                generator = get_generator(
                    dry_run=dry_run,
                    model_name=model_name,
                    adapter_path=local_adapter,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                raw_episodes = generator.generate([task], group_size)

            if raw_episodes is not None:
                episodes = score_group(raw_episodes)
                for kind, key in (
                    ("infra", "infra_error"),
                    ("scoring", "error"),
                ):
                    errors = [e[key] for e in episodes if e.get(key)]
                    info[f"num_{kind}_errors"] = len(errors)
                    if errors:
                        info[f"sample_{kind}_error"] = str(errors[0])[:800]
                if not is_live(run_dir, version):
                    info["dropped_stale"] = True
                    info["version"] = version
                else:
                    enqueue_group(run_dir, version, episodes)
                    info["version"] = version
                    info["enqueued"] = True
                    info["mean_reward"] = round(
                        sum(e["reward"] for e in episodes) / len(episodes), 4
                    )
    except Exception as e:
        info["infra_error"] = f"{type(e).__name__}: {e}"
    finally:
        if local_adapter:
            shutil.rmtree(local_adapter, ignore_errors=True)

    log_metadata(metadata=info)
