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
"""Execute static Python steps on Nebius Serverless GPU Jobs."""

import re
import time
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Type, cast
from uuid import uuid4

from zenml.client import Client
from zenml.config.build_configuration import BuildConfiguration
from zenml.enums import ExecutionStatus, StackComponentType
from zenml.integrations.nebius import job_client
from zenml.integrations.nebius.flavors import (
    NebiusStepOperatorConfig,
    NebiusStepOperatorSettings,
)
from zenml.integrations.nebius.submission import (
    IMAGE_KEY,
    RECEIPT_KEY,
    SubmissionReceipt,
)
from zenml.logger import get_logger
from zenml.orchestrators.publish_utils import publish_step_run_metadata
from zenml.stack import Stack, StackValidator
from zenml.step_operators import BaseStepOperator

if TYPE_CHECKING:
    from zenml.config.base_settings import BaseSettings
    from zenml.config.step_run_info import StepRunInfo
    from zenml.models import PipelineSnapshotBase, StepRunResponse

logger = get_logger(__name__)
TERMINAL_STATES = {"COMPLETED", "FAILED", "ERROR", "CANCELLED"}


class NebiusStepOperator(BaseStepOperator):
    """Run one Python step per Job, retaining identity across client failures.

    This experimental implementation supports static pipelines with a local
    orchestrator. It does not resume orchestration after process loss, retry
    workloads, or guarantee deletion of underlying Compute resources.
    """

    @property
    def config(self) -> NebiusStepOperatorConfig:
        """Return the component configuration.

        Returns:
            The Nebius configuration.
        """
        return cast(NebiusStepOperatorConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Return the workload settings class.

        Returns:
            The Nebius settings class.
        """
        return NebiusStepOperatorSettings

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validate the supported stack before any cloud submission.

        Returns:
            The stack validator.
        """

        def validate(stack: Stack) -> Tuple[bool, str]:
            if stack.artifact_store.config.is_local:
                return (
                    False,
                    "Nebius requires a remote artifact store accessible to the Job.",
                )
            registry = stack.container_registry
            if registry is None or registry.config.is_local:
                return False, "Nebius requires a remote container registry."
            if stack.orchestrator.flavor != "local":
                return (
                    False,
                    "The experimental Nebius operator currently supports the local orchestrator only.",
                )
            return True, ""

        return StackValidator(
            required_components={
                StackComponentType.CONTAINER_REGISTRY,
                StackComponentType.IMAGE_BUILDER,
            },
            custom_validation_function=validate,
        )

    def get_docker_builds(
        self, snapshot: "PipelineSnapshotBase"
    ) -> List[BuildConfiguration]:
        """Build the images for selected static steps through ZenML.

        Args:
            snapshot: The pipeline snapshot.

        Returns:
            Per-step build configurations.

        Raises:
            ValueError: If the snapshot is dynamic.
        """
        if snapshot.is_dynamic:
            raise ValueError(
                "Dynamic pipelines are not supported by the experimental Nebius operator."
            )
        return [
            BuildConfiguration(
                key=IMAGE_KEY,
                settings=step.config.docker_settings,
                step_name=name,
            )
            for name, step in snapshot.step_configurations.items()
            if step.config.uses_step_operator(self.name)
        ]

    def submit(
        self,
        info: "StepRunInfo",
        entrypoint_command: List[str],
        environment: Dict[str, str],
    ) -> None:
        """Submit once and return after cloud identity is acknowledged.

        Args:
            info: The existing ZenML step run.
            entrypoint_command: The standard ZenML entrypoint argv.
            environment: Runtime environment, including workload credentials.

        Raises:
            ValueError: If the step or its resources are unsupported.
            RuntimeError: If identity cannot be saved or submission is uncertain.
            BaseException: If submission is interrupted; acknowledged Jobs are
                canceled on a best-effort basis before propagating interruption.
        """
        if (
            info.snapshot.is_dynamic
            or info.config.command is not None
            or info.config.retry is not None
        ):
            raise ValueError(
                "Nebius supports static Python steps without automatic retries only."
            )
        resources = info.config.resource_settings.model_dump(
            exclude_defaults=True, exclude_none=True
        )
        if resources.pop("gpu_count", 1) != 1 or resources:
            raise ValueError(
                "Set Nebius platform/preset settings; only generic gpu_count=1 is supported."
            )
        if Client().zen_store.is_local_store():
            raise ValueError(
                "Nebius requires a remotely reachable ZenML server."
            )
        fresh = Client().get_run_step(info.step_run_id)
        if (
            RECEIPT_KEY in fresh.run_metadata
            or RECEIPT_KEY in info.step_run.run_metadata
        ):
            raise RuntimeError(
                "This step already has a Nebius submission receipt. Inspect it; do not resubmit."
            )
        settings = cast(NebiusStepOperatorSettings, self.get_settings(info))
        image = info.get_image(key=IMAGE_KEY)
        spec = job_client.build_spec(
            self.config, settings, image, entrypoint_command, environment
        )
        now = time.time()
        submission_id = str(uuid4())
        receipt = SubmissionReceipt(
            component_id=str(self.id),
            step_run_id=str(info.step_run_id),
            pipeline_run_id=str(info.run_id),
            project_id=self.config.project_id,
            subnet_id=self.config.subnet_id,
            submission_id=submission_id,
            name=f"zenml-{info.step_run_id}-{submission_id[:8]}",
            image=image,
            fingerprint=job_client.spec_fingerprint(spec),
            created_at=now,
            deadline=now + settings.total_timeout_seconds,
            provisioning_deadline=now + settings.provisioning_timeout_seconds,
            expected_outputs=list(info.config.outputs),
            request_timeout=settings.request_timeout_seconds,
            poll_interval=settings.poll_interval_seconds,
            cancel_timeout=settings.cancel_timeout_seconds,
            publication_grace=settings.publication_grace_seconds,
        )
        self._save(info.step_run, receipt)

        def acknowledged(operation_id: str, job_id: str) -> None:
            receipt.operation_id = operation_id or None
            receipt.job_id = job_id or None
            self._save(info.step_run, receipt)

        try:
            with job_client.connect(
                self.config, receipt.request_timeout
            ) as client:
                client.create(
                    job_client.create_request(receipt, spec),
                    submission_id,
                    acknowledged,
                )
        except BaseException as error:
            diagnostics = job_client.get_request_error_metadata(error)
            if diagnostics:
                receipt.submission_error_code = diagnostics.get(
                    "submission_error_code"
                )
                receipt.submission_request_id = diagnostics.get(
                    "submission_request_id"
                )
                try:
                    self._save(info.step_run, receipt)
                except Exception:
                    logger.warning(
                        "Cannot publish submission diagnostics; retaining the receipt locally."
                    )
            if receipt.job_id:
                self._best_effort_cancel(info.step_run, receipt)
            if not isinstance(error, Exception):
                logger.warning(
                    "Interrupted Nebius submission. Recovery receipt: %s",
                    receipt.model_dump_json(),
                )
                raise
            raise RuntimeError(
                "Nebius submission did not finish safely. Do not resubmit. "
                f"Recovery receipt: {receipt.model_dump_json()}"
            ) from None
        logger.info(
            "Nebius Job %s submitted. Logs: nebius ai job logs %s --follow",
            receipt.job_id,
            receipt.job_id,
        )

    def get_status(self, step_run: "StepRunResponse") -> ExecutionStatus:
        """Reconcile infrastructure with the published Python step outcome.

        Args:
            step_run: The existing step run.

        Returns:
            The reconciled status; zero exit without a published result fails.

        Raises:
            RuntimeError: If identity is missing or cloud status cannot be read.
        """
        receipt = self._load(step_run)
        if not receipt.job_id:
            raise RuntimeError(
                "Nebius submission is unknown; inspect the receipt and all matching Jobs."
            )
        try:
            with job_client.connect(
                self.config, receipt.request_timeout
            ) as client:
                job = client.get(receipt.job_id)
        except Exception:
            raise RuntimeError(
                f"Cannot read Nebius Job {receipt.job_id}; its cleanup is unconfirmed."
            ) from None
        if job.metadata.parent_id != receipt.project_id:
            raise RuntimeError(
                "Nebius Job project does not match the persisted receipt."
            )
        state = job.status.state.name
        receipt.provider_state = state
        code = job.status.state_details.code
        receipt.provider_code = (
            code
            if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,100}", code)
            else None
        )
        if state in TERMINAL_STATES:
            receipt.cleanup = "WORKLOAD_TERMINAL"
        if state == "COMPLETED" and receipt.completion_observed_at is None:
            receipt.completion_observed_at = time.time()
        self._save_if_changed(step_run, receipt)
        if state in {"FAILED", "ERROR"}:
            logger.error(
                "Nebius Job %s ended in %s (%s).",
                receipt.job_id,
                state,
                receipt.provider_code,
            )
            return ExecutionStatus.FAILED
        if state == "CANCELLED":
            return ExecutionStatus.CANCELLED
        if state == "COMPLETED":
            fresh = Client().get_run_step(step_run.id)
            if fresh.status == ExecutionStatus.COMPLETED and all(
                fresh.outputs.get(name) for name in receipt.expected_outputs
            ):
                return ExecutionStatus.COMPLETED
            if fresh.status.is_failed:
                return fresh.status
            assert receipt.completion_observed_at is not None
            if (
                time.time()
                >= receipt.completion_observed_at + receipt.publication_grace
            ):
                logger.error(
                    "Nebius Job %s completed without a successful ZenML result and expected artifacts.",
                    receipt.job_id,
                )
                return ExecutionStatus.FAILED
            return ExecutionStatus.RUNNING
        if state == "CANCELLING":
            return ExecutionStatus.CANCELLING
        if state == "RUNNING":
            return ExecutionStatus.RUNNING
        return ExecutionStatus.PROVISIONING

    def wait(self, step_run: "StepRunResponse") -> ExecutionStatus:
        """Wait with finite deadlines and forward interruption to the Job.

        Args:
            step_run: The existing step run.

        Returns:
            The reconciled terminal status.

        Raises:
            TimeoutError: If the supervision deadline expires.
            BaseException: If interrupted, after best-effort cancellation.
        """
        receipt = self._load(step_run)
        local_deadline = time.monotonic() + max(
            0, receipt.deadline - time.time()
        )
        provisioning_deadline = time.monotonic() + max(
            0, receipt.provisioning_deadline - time.time()
        )
        try:
            while True:
                if time.monotonic() >= local_deadline:
                    raise TimeoutError(
                        f"Nebius supervision timed out for Job {receipt.job_id}."
                    )
                try:
                    status = self.get_status(step_run)
                except Exception:
                    logger.warning(
                        "Nebius status unavailable; continuing only until the saved deadline."
                    )
                else:
                    if status.is_finished:
                        return status
                    if (
                        status == ExecutionStatus.PROVISIONING
                        and time.monotonic() >= provisioning_deadline
                    ):
                        raise TimeoutError(
                            f"Nebius provisioning timed out for Job {receipt.job_id}."
                        )
                    fresh = Client().get_run_step(step_run.id)
                    if fresh.status in {
                        ExecutionStatus.CANCELLING,
                        ExecutionStatus.CANCELLED,
                    }:
                        self.cancel(step_run)
                time.sleep(
                    min(
                        receipt.poll_interval,
                        max(0, local_deadline - time.monotonic()),
                    )
                )
        except BaseException:
            self._best_effort_cancel(step_run, receipt)
            raise

    def cancel(self, step_run: "StepRunResponse") -> None:
        """Cancel the acknowledged ID and bound confirmation independently.

        Args:
            step_run: The step whose cloud workload should stop.

        Raises:
            RuntimeError: If cancellation cannot be confirmed or identity is missing.
        """  # noqa: DOC502
        self._cancel_receipt(step_run, self._load(step_run))

    def cleanup_step_submission(self, step_run: "StepRunResponse") -> None:
        """Reconcile workload termination, retaining Job records and user data.

        Args:
            step_run: The submitted step run.
        """
        receipt = self._load(step_run)
        if receipt.cleanup == "WORKLOAD_TERMINAL":
            return
        self._best_effort_cancel(step_run, receipt)

    def find_submission_jobs(self, step_run: "StepRunResponse") -> List[str]:
        """List candidate Jobs for manual recovery without changing any resource.

        Args:
            step_run: The step with a previously saved receipt.

        Returns:
            All matching candidates; zero matches does not prove no Job exists.

        Raises:
            RuntimeError: If the bounded search cannot finish.
        """
        receipt = self._load(step_run)
        try:
            with job_client.connect(
                self.config, receipt.request_timeout
            ) as client:
                return client.find_candidates(receipt)
        except Exception:
            raise RuntimeError(
                "Nebius recovery search failed or was incomplete. Do not resubmit."
            ) from None

    def _load(self, step_run: "StepRunResponse") -> SubmissionReceipt:
        """Load current identity and validate component ownership.

        Args:
            step_run: The supplied run, used as fallback during a server outage.

        Returns:
            The saved receipt.

        Raises:
            RuntimeError: If no receipt exists or ownership does not match.
        """
        metadata = step_run.run_metadata
        try:
            fresh = Client().get_run_step(step_run.id)
            metadata = fresh.run_metadata
        except Exception:
            pass
        candidates = [
            SubmissionReceipt.model_validate_json(raw)
            for raw in (
                metadata.get(RECEIPT_KEY),
                step_run.run_metadata.get(RECEIPT_KEY),
            )
            if isinstance(raw, str)
        ]
        if not candidates:
            raise RuntimeError(
                "Missing Nebius submission receipt; no cloud action was taken."
            )
        receipt = max(candidates, key=lambda candidate: candidate.revision)
        if (
            receipt.component_id != str(self.id)
            or receipt.step_run_id != str(step_run.id)
            or receipt.project_id != self.config.project_id
        ):
            raise RuntimeError(
                "Nebius receipt ownership does not match this component and step."
            )
        return receipt

    def _save(
        self, step_run: "StepRunResponse", receipt: SubmissionReceipt
    ) -> None:
        """Persist identity, keeping acknowledged IDs locally on store failure.

        Args:
            step_run: The step being updated.
            receipt: The non-secret receipt.
        """
        receipt.revision += 1
        payload = receipt.model_dump_json()
        step_run.run_metadata[RECEIPT_KEY] = payload
        publish_step_run_metadata(
            step_run.id, {self.id: {RECEIPT_KEY: payload}}
        )

    def _save_if_changed(
        self, step_run: "StepRunResponse", receipt: SubmissionReceipt
    ) -> None:
        """Avoid repeatedly publishing identical status metadata.

        Args:
            step_run: The step being updated.
            receipt: The latest non-secret receipt.
        """
        if step_run.run_metadata.get(RECEIPT_KEY) != receipt.model_dump_json():
            self._save(step_run, receipt)

    def _cancel_receipt(
        self, step_run: "StepRunResponse", receipt: SubmissionReceipt
    ) -> None:
        """Cancel once per saved receipt and poll for terminal state.

        Args:
            step_run: The existing step run.
            receipt: Identity that may not yet have reached the ZenML server.

        Raises:
            RuntimeError: If the Job cannot be identified or termination is unconfirmed.
        """
        if not receipt.job_id:
            raise RuntimeError(
                "No acknowledged Nebius Job ID; cancellation was not attempted."
            )
        deadline = time.monotonic() + receipt.cancel_timeout
        try:
            with job_client.connect(
                self.config,
                min(receipt.request_timeout, receipt.cancel_timeout),
            ) as client:
                try:
                    job = client.get(receipt.job_id)
                    if job.status.state.name in TERMINAL_STATES:
                        self._record_terminal(
                            step_run, receipt, job.status.state.name
                        )
                        return
                except Exception:
                    pass
                if not receipt.cancellation_requested:
                    receipt.cancellation_requested = True
                    try:
                        self._save(step_run, receipt)
                    except Exception:
                        logger.warning(
                            "Cannot save cancellation intent; retaining the acknowledged Job ID locally."
                        )
                    try:
                        client.cancel(
                            receipt.job_id, f"{receipt.submission_id}-cancel"
                        )
                    except Exception:
                        logger.warning(
                            "Cancel acknowledgement unavailable for Job %s; checking status without replay.",
                            receipt.job_id,
                        )
                while time.monotonic() < deadline:
                    client.timeout = min(
                        receipt.request_timeout,
                        max(0.1, deadline - time.monotonic()),
                    )
                    try:
                        job = client.get(receipt.job_id)
                        if job.status.state.name in TERMINAL_STATES:
                            self._record_terminal(
                                step_run, receipt, job.status.state.name
                            )
                            return
                    except Exception:
                        pass
                    time.sleep(
                        min(
                            receipt.poll_interval,
                            max(0, deadline - time.monotonic()),
                        )
                    )
        except Exception:
            pass
        receipt.cleanup = "UNCONFIRMED"
        try:
            self._save(step_run, receipt)
        except Exception:
            pass
        raise RuntimeError(
            f"Cancellation of Nebius Job {receipt.job_id} is unconfirmed. Inspect the Job and Compute resources; do not resubmit."
        )

    def _record_terminal(
        self,
        step_run: "StepRunResponse",
        receipt: SubmissionReceipt,
        state: str,
    ) -> None:
        """Retain a terminal observation even if metadata publication fails.

        Args:
            step_run: The step being updated.
            receipt: The acknowledged submission identity.
            state: The observed terminal provider state.
        """
        receipt.provider_state = state
        receipt.cleanup = "WORKLOAD_TERMINAL"
        try:
            self._save(step_run, receipt)
        except Exception:
            logger.warning(
                "Cannot publish terminal state for Job %s; the receipt is retained locally.",
                receipt.job_id,
            )

    def _best_effort_cancel(
        self, step_run: "StepRunResponse", receipt: SubmissionReceipt
    ) -> None:
        """Report cleanup failure without replacing the original exception.

        Args:
            step_run: The existing step run.
            receipt: The most recently acknowledged identity.
        """
        try:
            latest = self._load(step_run)
            if latest.revision > receipt.revision:
                receipt = latest
            self._cancel_receipt(step_run, receipt)
        except Exception:
            logger.warning(
                "Nebius cleanup unconfirmed. Recovery receipt: %s",
                receipt.model_dump_json(),
            )
