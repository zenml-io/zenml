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
"""Typed Nebius SDK boundary with bounded requests and no mutation retries."""

import hashlib
import json
import re
import time
from contextlib import contextmanager
from datetime import timedelta
from typing import Callable, Dict, Iterator, List

from nebius.api.nebius.ai.v1 import (
    CancelJobRequest,
    CreateJobRequest,
    GetJobRequest,
    Job,
    JobServiceClient,
    JobSpec,
    ListJobsRequest,
)
from nebius.api.nebius.common.v1 import ResourceMetadata
from nebius.api.nebius.compute.v1 import DiskSpec
from nebius.sdk import SDK

from zenml.integrations.nebius.flavors import (
    NebiusStepOperatorConfig,
    NebiusStepOperatorSettings,
)
from zenml.integrations.nebius.remote_bootstrap import ARGV_PATH, encode_argv
from zenml.integrations.nebius.submission import SubmissionReceipt
from zenml.logger import get_logger

logger = get_logger(__name__)


class JobClient:
    """A client scoped to one operator call, never serialized with the stack."""

    def __init__(self, sdk: SDK, timeout: float) -> None:
        """Initialize the client.

        Args:
            sdk: The caller-owned SDK.
            timeout: Maximum duration of each request, including authorization.
        """
        self.service = JobServiceClient(sdk)
        self.timeout = timeout

    def create(
        self,
        request: CreateJobRequest,
        key: str,
        acknowledged: Callable[[str, str], None],
    ) -> str:
        """Create once, persisting operation identity before further reads.

        Args:
            request: The generated request.
            key: The persisted idempotency key.
            acknowledged: Callback to persist operation and resource IDs.

        Returns:
            The acknowledged Job ID.

        Raises:
            RuntimeError: If the operation has no resource ID after completion.
        """
        operation = self.service.create(
            request,
            metadata=[("x-idempotency-key", key)],
            retries=0,
            timeout=self.timeout,
            auth_timeout=self.timeout,
        ).wait()
        acknowledged(operation.id, operation.resource_id)
        if not operation.resource_id:
            operation.sync_wait(
                timeout=self.timeout,
                poll_iteration_timeout=self.timeout,
                poll_retries=0,
            )
            acknowledged(operation.id, operation.resource_id)
        if not operation.resource_id:
            raise RuntimeError("Nebius Create returned no Job ID.")
        return operation.resource_id

    def get(self, job_id: str) -> Job:
        """Read one Job with a bounded request.

        Args:
            job_id: The acknowledged resource ID.

        Returns:
            The Job, without requesting sensitive data.
        """
        return self.service.get(
            GetJobRequest(id=job_id),
            retries=0,
            timeout=self.timeout,
            auth_timeout=self.timeout,
        ).wait()

    def cancel(self, job_id: str, key: str) -> None:
        """Send one cancellation; callers confirm terminal state separately.

        Args:
            job_id: The acknowledged resource ID.
            key: Stable cancellation idempotency key.
        """
        self.service.cancel(
            CancelJobRequest(id=job_id),
            metadata=[("x-idempotency-key", key)],
            retries=0,
            timeout=self.timeout,
            auth_timeout=self.timeout,
        ).wait()

    def find_candidates(self, receipt: SubmissionReceipt) -> List[str]:
        """Inspect all project pages for matching submission labels.

        Args:
            receipt: The original, non-secret submission receipt.

        Returns:
            Candidate IDs for manual investigation, never automatic replay.

        Raises:
            RuntimeError: If pagination is incomplete or repeats a token.
        """
        candidates = []
        token = ""
        seen = set()
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            response = self.service.list(
                ListJobsRequest(
                    parent_id=receipt.project_id,
                    page_size=100,
                    page_token=token,
                ),
                retries=0,
                timeout=max(0.1, deadline - time.monotonic()),
                auth_timeout=max(0.1, deadline - time.monotonic()),
            ).wait()
            for job in response.items:
                if (
                    job.metadata.parent_id == receipt.project_id
                    and job.metadata.labels.get("zenml-submission")
                    == receipt.submission_id
                    and job.metadata.labels.get("zenml-step")
                    == receipt.step_run_id
                    and job.metadata.labels.get("zenml-fingerprint")
                    == receipt.fingerprint
                    and job.spec.image == receipt.image
                    and job.spec.subnet_id == receipt.subnet_id
                ):
                    candidates.append(job.metadata.id)
            token = response.next_page_token
            if not token:
                return candidates
            if token in seen:
                break
            seen.add(token)
        raise RuntimeError(
            "Nebius recovery listing was incomplete; do not resubmit."
        )


@contextmanager
def connect(
    config: NebiusStepOperatorConfig, timeout: float
) -> Iterator[JobClient]:
    """Open and close a launcher-only SDK.

    Args:
        config: The stable component configuration.
        timeout: Request budget in seconds.

    Yields:
        A bounded Jobs client.
    """
    sdk = SDK(credentials_file_name=config.credentials_file)
    try:
        yield JobClient(sdk, timeout)
    finally:
        try:
            sdk.sync_close(timeout=5)
        except Exception:
            logger.warning(
                "Failed to close the Nebius SDK; cloud cleanup is separate."
            )


def build_spec(
    config: NebiusStepOperatorConfig,
    settings: NebiusStepOperatorSettings,
    image: str,
    command: List[str],
    environment: Dict[str, str],
) -> JobSpec:
    """Build a single-GPU Job without serializing credentials into the image.

    Args:
        config: Project and authentication configuration.
        settings: Resolved per-step workload settings.
        image: Immutable image reference from the ZenML build.
        command: Standard ZenML step argv.
        environment: Runtime environment supplied by ZenML.

    Returns:
        A generated Job specification.

    Raises:
        ValueError: If resources, image identity or environment are invalid.
    """
    if not settings.platform or not settings.preset:
        raise ValueError(
            "Set an explicit Nebius GPU platform and single-GPU preset."
        )
    if not re.fullmatch(r"[^\s@]+@sha256:[0-9a-f]{64}", image):
        raise ValueError(
            "Nebius requires a built image pinned by sha256 digest."
        )
    variables = []
    for name, value in environment.items():
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) or "\0" in value:
            raise ValueError("Invalid runtime environment variable.")
        variables.append(JobSpec.EnvironmentVariable(name=name, value=value))
    for name, version in settings.environment_secret_versions.items():
        if name in environment or name.startswith("ZENML_"):
            raise ValueError(
                "Native secret references may not override the ZenML runtime environment."
            )
        if not re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*", name
        ) or not version.startswith("mbsecver-"):
            raise ValueError(
                "Native secrets require valid environment names and secret version IDs."
            )
        variables.append(
            JobSpec.EnvironmentVariable(
                name=name,
                mysterybox_secret=JobSpec.MysteryBoxSecretRef(
                    version_id=version
                ),
            )
        )
    registry = None
    if config.registry_secret_version:
        registry = JobSpec.RegistryCredentials(
            mysterybox_secret_version=config.registry_secret_version
        )
    return JobSpec(
        image=image,
        platform=settings.platform,
        preset=settings.preset,
        subnet_id=config.subnet_id,
        disk=JobSpec.DiskSpec(
            type=DiskSpec.DiskType.NETWORK_SSD,
            size_bytes=settings.disk_size_gib * 1024**3,
        ),
        shm_size_bytes=settings.shm_size_gib * 1024**3,
        public_ip=settings.public_ip,
        preemptible=False,
        restart_attempts=0,
        timeout=timedelta(seconds=settings.timeout_seconds),
        container_command="python",
        args=f"-m zenml.integrations.nebius.remote_bootstrap {ARGV_PATH}",
        environment_variables=variables,
        registry_credentials=registry,
        injected_files=[
            JobSpec.FileInjection(
                container_path=ARGV_PATH, content=encode_argv(command)
            )
        ],
    )


def spec_fingerprint(spec: JobSpec) -> str:
    """Fingerprint non-secret resources and the standard entrypoint.

    Args:
        spec: The Job specification.

    Returns:
        A fingerprint that excludes runtime credential values.
    """
    public = {
        "image": spec.image,
        "platform": spec.platform,
        "preset": spec.preset,
        "subnet": spec.subnet_id,
        "disk": spec.disk.size_bytes,
        "shm": spec.shm_size_bytes,
        "public_ip": spec.public_ip,
        "timeout": spec.timeout.total_seconds() if spec.timeout else None,
        "argv": [file.content.decode("utf-8") for file in spec.injected_files],
        "environment": sorted(
            variable.name for variable in spec.environment_variables
        ),
        "secret_versions": sorted(
            (variable.name, variable.mysterybox_secret.version_id)
            for variable in spec.environment_variables
        ),
        "registry_version": spec.registry_credentials.mysterybox_secret_version,
    }
    return hashlib.sha256(
        json.dumps(public, sort_keys=True).encode()
    ).hexdigest()


def create_request(
    receipt: SubmissionReceipt, spec: JobSpec
) -> CreateJobRequest:
    """Attach persisted identity to the Job specification.

    Args:
        receipt: The pre-published submission identity.
        spec: The generated specification.

    Returns:
        A request with identity labels for read-only recovery.
    """
    return CreateJobRequest(
        metadata=ResourceMetadata(
            parent_id=receipt.project_id,
            name=receipt.name,
            labels={
                "zenml-submission": receipt.submission_id,
                "zenml-step": receipt.step_run_id,
                "zenml-run": receipt.pipeline_run_id,
                "zenml-fingerprint": receipt.fingerprint,
            },
        ),
        spec=spec,
    )
