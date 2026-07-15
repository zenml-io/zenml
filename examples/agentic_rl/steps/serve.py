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
"""Serve the trained checkpoint as a run-scoped policy service.

This is the "after-eval" leg: once training has produced a checkpoint,
stand the policy up behind an HTTP endpoint (vLLM's OpenAI-compatible
server) so it can be probed, and — eventually — evaluated by agents that
call it. The service handle is persisted by ``ServiceMaterializer``, so
"which checkpoint is this server serving" is answerable from lineage:
the service's ``config.command`` names the weights, and the
``checkpoint_dir`` input edge joins it back to the training run.

Teardown is a two-layer contract. The happy path is the
``stop_policy_service`` step, which deprovisions the pod at the end of
the run. The *guarantee* is ``max_lifetime_seconds``: the pod carries its
own deadline, so a GPU server leaked by a crashed run (the step that
would have stopped it never executed) self-terminates instead of billing
indefinitely.
"""

import json
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from typing_extensions import Annotated

from zenml import log_metadata, step
from zenml.client import Client
from zenml.logger import get_logger
from zenml.services import BaseService

logger = get_logger(__name__)


def _register_policy_service(service: BaseService) -> None:
    """Register the ACTIVE service with the ZenML server, best effort.

    Registration makes the running service queryable server-side (via
    ``Client().get_service`` / ``list_services``) and across runs, instead
    of living only inside the returned artifact handle. It is bookkeeping:
    serving has already succeeded by the time this runs, so a failure to
    reach the server — a bare/hermetic environment, a transient outage, a
    name collision with a prior run's record — must never fail the step.
    Such failures are logged and swallowed.

    Args:
        service: The provisioned, ACTIVE policy service to register.
    """
    try:
        client = Client()
        response = client.create_service(
            config=service.config,
            service_type=service.SERVICE_TYPE,
        )
        client.update_service(
            id=response.id,
            name=service.config.service_name,
            service_source=service.model_dump().get("type"),
            admin_state=service.admin_state,
            status=service.status.model_dump(),
            endpoint=service.endpoint.model_dump()
            if service.endpoint
            else None,
        )
    except Exception as error:
        logger.warning(
            "Could not register the policy service with the ZenML server: "
            "%s. Serving is unaffected; the service just won't be queryable "
            "server-side.",
            error,
        )


def _mark_policy_service_stopped(service: BaseService) -> None:
    """Reflect the stopped state on the server-side record, best effort.

    Mirrors ``_register_policy_service``: once the pod is deprovisioned,
    update the tracked record so server state matches reality. The record
    is looked up by its deterministic service name because the step holds
    the service handle, not the server-assigned id. Never raises, for the
    same reason ``stop_policy_service`` never raises — teardown bookkeeping
    must not mask the run's outcome.

    Args:
        service: The deprovisioned policy service.
    """
    try:
        client = Client()
        record = client.get_service(
            service.config.service_name,
            allow_name_prefix_match=False,
        )
        client.update_service(
            id=record.id,
            admin_state=service.admin_state,
            status=service.status.model_dump(),
        )
    except Exception as error:
        logger.debug(
            "Could not update the policy service record after teardown: %s.",
            error,
        )


@step(enable_cache=False)
def serve_checkpoint(
    checkpoint_dir: Optional[str],
    image: str,
    port: int = 8000,
    gpu_count: int = 1,
    max_lifetime_seconds: int = 3600,
    model_name: str = "policy",
) -> Annotated[BaseService, "policy_service"]:
    """Serve a trained checkpoint behind a vLLM HTTP endpoint.

    A ``KubernetesPodService`` is provisioned to run
    ``vllm serve <checkpoint_dir>`` and waited on until it reports
    ``ACTIVE`` (or the startup timeout elapses). The returned service is
    persisted by ``ServiceMaterializer`` as the ``policy_service``
    artifact: the served checkpoint is recoverable from lineage because
    the service config records the launch command and this step's
    ``checkpoint_dir`` input is the edge back to the run that produced
    the weights.

    ``checkpoint_dir`` must live on storage the serving pod can mount and
    read — the same shared-storage requirement the trainer and ingest
    steps already have (an RWX PV on Kubernetes, the local filesystem on
    a single machine). Mounting that storage into the pod is a
    ``pod_settings`` concern threaded as a step setting; it is
    intentionally out of scope for this v1 and the pod is launched with
    the checkpoint path passed through verbatim.

    Teardown contract: the happy path is the ``stop_policy_service`` step
    downstream, which deprovisions this pod at the end of the run. The
    backstop is ``max_lifetime_seconds`` — the pod self-terminates at
    that deadline, so a GPU server leaked by a crashed run does not bill
    forever.

    Args:
        checkpoint_dir: The HF-format weights directory to serve
            (``find_checkpoint``'s output). ``None`` means the trainer
            produced no checkpoint.
        image: The serving container image (e.g. a vLLM image).
        port: The port vLLM listens on inside the pod.
        gpu_count: GPUs to request for the serving pod.
        max_lifetime_seconds: The pod's self-termination deadline — the
            GC backstop for a leaked server.
        model_name: The vLLM ``--served-model-name`` the policy is
            exposed under.

    Returns:
        The provisioned, ACTIVE policy service.

    Raises:
        RuntimeError: If ``checkpoint_dir`` is ``None`` (the trainer ran
            without ``--ckpt``, so there is nothing to serve) or the
            service never became ACTIVE within the startup timeout.
    """
    if checkpoint_dir is None:
        raise RuntimeError(
            "Nothing to serve: checkpoint_dir is None. The trainer ran "
            "without --ckpt (or emitted no weights/step_N dir), so there "
            "is no policy to stand up. Re-run training with --ckpt."
        )

    # Imported lazily so the example (and its hermetic tests) import
    # without the kubernetes extra installed.
    from zenml.integrations.kubernetes.services import (
        KubernetesPodService,
        KubernetesPodServiceConfig,
    )

    service = KubernetesPodService(
        config=KubernetesPodServiceConfig(
            name=f"policy-{model_name}",
            image=image,
            command=[
                "bash",
                "-lc",
                f"vllm serve {checkpoint_dir} "
                f"--served-model-name {model_name} --port {port}",
            ],
            port=port,
            gpu_count=gpu_count,
            max_lifetime_seconds=max_lifetime_seconds,
        )
    )

    # start() sets the admin state, provisions the pod, and polls until
    # the operational state catches up or the timeout elapses; it does
    # not raise on timeout, so the ACTIVE state is asserted explicitly.
    service.start(timeout=600)
    if not service.is_running:
        raise RuntimeError(
            f"Policy service did not become ACTIVE within the startup "
            f"timeout.\n{service.get_service_status_message()}"
        )

    log_metadata(
        metadata={
            "policy_service.model_name": model_name,
            "policy_service.checkpoint_dir": checkpoint_dir,
            "policy_service.image": image,
            "policy_service.max_lifetime_seconds": max_lifetime_seconds,
        }
    )
    logger.info("Policy service is ACTIVE at %s.", service.url)
    _register_policy_service(service)
    return service


@step(enable_cache=False)
def probe_policy_service(service: BaseService) -> Dict[str, Any]:
    """Prove the served policy is reachable, from the step (not a sandbox).

    Hits ``{service.url}/v1/models`` over HTTP and records whether the
    endpoint answered, which models it lists, and the round-trip latency.
    This closes the service-lifecycle loop — provision, reach, tear down
    — and demonstrates the lineage join (the probed service is the one
    serving this run's checkpoint) end to end.

    The probe deliberately runs *from the ZenML step*, not from inside a
    Harbor sandbox. The full "eval agents call the served policy" leg
    needs a Harbor agent that calls an arbitrary endpoint plus sandbox
    egress to it — neither exists yet, and this step does not pretend
    they do (see the README).

    Only ``service.url`` is read, so any object exposing that attribute
    works — the step does not depend on the concrete service class.

    Args:
        service: The policy service to probe (reads ``.url`` only).

    Returns:
        The probe result: ``reachable``, the listed ``models``, the
        endpoint ``url``, and ``latency_seconds`` (``None`` when
        unreachable).
    """
    url = f"{service.url.rstrip('/')}/v1/models"
    result: Dict[str, Any] = {
        "url": url,
        "reachable": False,
        "models": [],
        "latency_seconds": None,
    }
    started = time.monotonic()
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        result["reachable"] = True
        result["latency_seconds"] = round(time.monotonic() - started, 4)
        result["models"] = [
            entry.get("id")
            for entry in payload.get("data", [])
            if isinstance(entry, dict)
        ]
        logger.info(
            "Policy service reachable at %s (models: %s).",
            url,
            result["models"],
        )
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as error:
        result["error"] = str(error)
        logger.warning("Policy service probe failed for %s: %s", url, error)

    log_metadata(
        metadata={
            "probe.reachable": result["reachable"],
            "probe.url": url,
            "probe.models": result["models"],
            "probe.latency_seconds": result["latency_seconds"],
        }
    )
    return result


@step(enable_cache=False)
def stop_policy_service(service: BaseService) -> None:
    """Tear the policy service down. Idempotent; never raises.

    The happy-path half of the teardown contract: at the end of a run
    this deprovisions the serving pod so the GPU is released promptly
    rather than waiting on the ``max_lifetime_seconds`` backstop. It is
    written to never raise — a teardown step that fails would mask the
    run's real outcome, and the pod's own deadline is the guarantee that
    a missed stop still frees the GPU.

    Order this after ``probe_policy_service`` with the invocation-level
    ``after=`` argument (ZenML reserves ``after`` as a step keyword, so
    it cannot be a step parameter).

    Args:
        service: The policy service to deprovision.
    """
    try:
        service.stop(timeout=120)
        logger.info("Policy service stopped.")
    except Exception as error:
        logger.warning(
            "Policy service teardown did not complete cleanly: %s. The "
            "pod's max_lifetime_seconds deadline remains the backstop.",
            error,
        )
    _mark_policy_service_stopped(service)
