#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Kubernetes step operator implementation."""

import random
import shlex
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Type, cast

from kubernetes import client as k8s_client

from zenml.config.base_settings import BaseSettings
from zenml.config.build_configuration import BuildConfiguration
from zenml.enums import ExecutionStatus, StackComponentType
from zenml.integrations.kubernetes import kube_utils
from zenml.integrations.kubernetes.constants import (
    STEP_NAME_ANNOTATION_KEY,
    STEP_OPERATOR_ANNOTATION_KEY,
)
from zenml.integrations.kubernetes.flavors import (
    KubernetesStepOperatorConfig,
    KubernetesStepOperatorSettings,
)
from zenml.integrations.kubernetes.manifest_utils import (
    build_job_manifest,
    build_pod_manifest,
    pod_template_manifest_from_pod,
)
from zenml.logger import get_logger
from zenml.stack import Stack, StackValidator
from zenml.step_operators import BaseStepOperator

if TYPE_CHECKING:
    from zenml.config.step_run_info import StepRunInfo
    from zenml.models import PipelineSnapshotBase, StepRunResponse

logger = get_logger(__name__)

KUBERNETES_STEP_OPERATOR_DOCKER_IMAGE_KEY = "kubernetes_step_operator"
STEP_JOB_NAME_METADATA_KEY = "job_name"

# Rendezvous port injected into multi-node command steps. Launchers that
# need a different port own their own flags (torchrun --master-port).
MULTI_NODE_RENDEZVOUS_PORT = 29500


def validate_multi_node_step(
    node_count: int, is_command_step: bool, step_name: str
) -> None:
    """Gate multi-node execution on command steps.

    A multi-node job runs the same entrypoint on every node. A regular
    step would duplicate its artifacts, outputs and logs across nodes,
    so only command steps — which own their distributed launch
    (torchrun, prime-rl entrypoints, Ray) — may scale out.

    Args:
        node_count: The requested node count.
        is_command_step: Whether the step is a command step.
        step_name: The step name, for the error message.

    Raises:
        RuntimeError: If a regular step requests more than one node.
    """
    if node_count > 1 and not is_command_step:
        raise RuntimeError(
            f"The step `{step_name}` requests node_count={node_count} "
            "but is a regular step. Running a regular step on multiple "
            "nodes would duplicate its artifacts, outputs and logs "
            "across every node. Use a CommandStep that owns its "
            "distributed launch instead, e.g. "
            '`CommandStep(command=["bash", "-lc", "torchrun '
            "--nnodes=$ZENML_NODE_COUNT --node-rank=$JOB_COMPLETION_INDEX "
            "--master-addr=$ZENML_MASTER_ADDR "
            '--master-port=$ZENML_MASTER_PORT train.py"])`. '
            "Keep node_count=1 for regular steps."
        )


def multi_node_environment(
    job_name: str, namespace: str, node_count: int
) -> Dict[str, str]:
    """Rendezvous environment for the pods of a multi-node job.

    The per-pod rank is NOT included here: Kubernetes injects
    ``JOB_COMPLETION_INDEX`` into every pod of an indexed job.

    Args:
        job_name: The job name (also the headless service name).
        namespace: The Kubernetes namespace.
        node_count: The number of pods.

    Returns:
        Environment variables shared by all pods of the job.
    """
    # Indexed-job pods get the hostname `<job-name>-<index>`; with the
    # pod spec's subdomain pointing at the headless service, index 0
    # resolves at this stable DNS name.
    return {
        "ZENML_NODE_COUNT": str(node_count),
        "ZENML_MASTER_ADDR": f"{job_name}-0.{job_name}.{namespace}.svc",
        "ZENML_MASTER_PORT": str(MULTI_NODE_RENDEZVOUS_PORT),
    }


def build_rank_dispatch_command(
    zenml_entrypoint_command: List[str], raw_command: List[str]
) -> List[str]:
    """Shell dispatch: rank 0 runs ZenML's entrypoint, other ranks the command.

    Every pod of an indexed job runs the same template, but only ONE pod
    may run the ZenML step entrypoint: it executes ``StepRunner.run``
    for the step run id, and N concurrent runners would race on status
    updates, the step logs record, and the success publish — the losers
    exit non-zero and fail the job even when the workload succeeded.
    Rank 0 therefore runs the full entrypoint (which executes the
    command step's command as its step function); every other rank runs
    the raw command directly — correct SPMD semantics, since the
    command owns its distributed launch and reads its rank from
    ``JOB_COMPLETION_INDEX``.

    Args:
        zenml_entrypoint_command: ZenML's step entrypoint command.
        raw_command: The command step's configured command.

    Returns:
        A single ``sh -c`` command implementing the dispatch.
    """
    zenml_part = shlex.join(zenml_entrypoint_command)
    raw_part = shlex.join(raw_command)
    script = (
        'if [ "${JOB_COMPLETION_INDEX:-0}" = "0" ]; then '
        f"exec {zenml_part}; "
        f"else exec {raw_part}; fi"
    )
    return ["/bin/sh", "-c", script]


def apply_indexed_completion(
    job_manifest: k8s_client.V1Job, node_count: int
) -> None:
    """Turn a single-pod job manifest into an indexed multi-pod job.

    Args:
        job_manifest: The job manifest to modify in place.
        node_count: The number of pods to run in parallel.
    """
    job_manifest.spec.parallelism = node_count
    job_manifest.spec.completions = node_count
    job_manifest.spec.completion_mode = "Indexed"
    # Stable per-pod DNS: hostname is set by Kubernetes for indexed
    # jobs; the subdomain ties it to the headless service (same name
    # as the job).
    job_manifest.spec.template.spec.subdomain = job_manifest.metadata.name


def build_headless_service_manifest(
    job: k8s_client.V1Job,
) -> k8s_client.V1Service:
    """Headless discovery service for the pods of a multi-node job.

    The service is owned by the job, so Kubernetes garbage collection
    removes it with the job (TTL, cancellation, deletion) — teardown
    must not depend on step code running.

    Args:
        job: The created job (its uid anchors the owner reference).

    Returns:
        The service manifest.
    """
    job_name = job.metadata.name
    return k8s_client.V1Service(
        metadata=k8s_client.V1ObjectMeta(
            name=job_name,
            labels=job.metadata.labels,
            owner_references=[
                k8s_client.V1OwnerReference(
                    api_version="batch/v1",
                    kind="Job",
                    name=job_name,
                    uid=job.metadata.uid,
                    controller=False,
                    block_owner_deletion=False,
                )
            ],
        ),
        spec=k8s_client.V1ServiceSpec(
            cluster_ip="None",
            # Kubernetes labels every pod of a job with job-name.
            selector={"job-name": job_name},
            ports=[
                k8s_client.V1ServicePort(
                    name="rendezvous", port=MULTI_NODE_RENDEZVOUS_PORT
                )
            ],
            # Pods must be resolvable during startup, before readiness.
            publish_not_ready_addresses=True,
        ),
    )


class KubernetesStepOperator(BaseStepOperator):
    """Step operator to run on Kubernetes."""

    _k8s_client: Optional[k8s_client.ApiClient] = None

    @property
    def config(self) -> KubernetesStepOperatorConfig:
        """Returns the `KubernetesStepOperatorConfig` config.

        Returns:
            The configuration.
        """
        return cast(KubernetesStepOperatorConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the Kubernetes step operator.

        Returns:
            The settings class.
        """
        return KubernetesStepOperatorSettings

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validates the stack.

        Returns:
            A validator that checks that the stack contains a remote container
            registry and a remote artifact store.
        """

        def _validate_remote_components(stack: "Stack") -> Tuple[bool, str]:
            if stack.artifact_store.config.is_local:
                return False, (
                    "The Kubernetes step operator runs code remotely and "
                    "needs to write files into the artifact store, but the "
                    f"artifact store `{stack.artifact_store.name}` of the "
                    "active stack is local. Please ensure that your stack "
                    "contains a remote artifact store when using the Vertex "
                    "step operator."
                )

            container_registry = stack.container_registry
            assert container_registry is not None

            if container_registry.config.is_local:
                return False, (
                    "The Kubernetes step operator runs code remotely and "
                    "needs to push/pull Docker images, but the "
                    f"container registry `{container_registry.name}` of the "
                    "active stack is local. Please ensure that your stack "
                    "contains a remote container registry when using the "
                    "Kubernetes step operator."
                )

            return True, ""

        return StackValidator(
            required_components={
                StackComponentType.CONTAINER_REGISTRY,
                StackComponentType.IMAGE_BUILDER,
            },
            custom_validation_function=_validate_remote_components,
        )

    def get_docker_builds(
        self, snapshot: "PipelineSnapshotBase"
    ) -> List["BuildConfiguration"]:
        """Gets the Docker builds required for the component.

        Args:
            snapshot: The pipeline snapshot for which to get the builds.

        Returns:
            The required Docker builds.
        """
        builds = []
        for step_name, step in snapshot.step_configurations.items():
            if step.config.uses_step_operator(self.name):
                build = BuildConfiguration(
                    key=KUBERNETES_STEP_OPERATOR_DOCKER_IMAGE_KEY,
                    settings=step.config.docker_settings,
                    step_name=step_name,
                )
                builds.append(build)

        return builds

    def get_kube_client(self) -> k8s_client.ApiClient:
        """Get the Kubernetes API client.

        Returns:
            The Kubernetes API client.

        Raises:
            RuntimeError: If the service connector returns an unexpected client.
        """
        if self.config.incluster:
            kube_utils.load_kube_config(incluster=True)
            self._k8s_client = k8s_client.ApiClient()
            return self._k8s_client

        # Refresh the client also if the connector has expired
        if self._k8s_client and not self.connector_has_expired():
            return self._k8s_client

        connector = self.get_connector()
        if connector:
            client = connector.connect()
            if not isinstance(client, k8s_client.ApiClient):
                raise RuntimeError(
                    f"Expected a k8s_client.ApiClient while trying to use the "
                    f"linked connector, but got {type(client)}."
                )
            self._k8s_client = client
        else:
            kube_utils.load_kube_config(
                context=self.config.kubernetes_context,
            )
            self._k8s_client = k8s_client.ApiClient()

        return self._k8s_client

    @property
    def _k8s_core_api(self) -> k8s_client.CoreV1Api:
        """Getter for the Kubernetes Core API client.

        Returns:
            The Kubernetes Core API client.
        """
        return k8s_client.CoreV1Api(self.get_kube_client())

    @property
    def _k8s_batch_api(self) -> k8s_client.BatchV1Api:
        """Getter for the Kubernetes Batch API client.

        Returns:
            The Kubernetes Batch API client.
        """
        return k8s_client.BatchV1Api(self.get_kube_client())

    def submit(
        self,
        info: "StepRunInfo",
        entrypoint_command: List[str],
        environment: Dict[str, str],
    ) -> None:
        """Submits a step run to Kubernetes.

        Args:
            info: Information about the step run.
            entrypoint_command: Command that executes the step.
            environment: Environment variables to set in the step operator
                environment.
        """
        settings = cast(
            KubernetesStepOperatorSettings, self.get_settings(info)
        )
        # Runs at submit time because dynamic pipelines execute from a
        # server-side snapshot where no compile-time hook is available.
        validate_multi_node_step(
            node_count=settings.node_count,
            is_command_step=info.config.command is not None,
            step_name=info.pipeline_step_name,
        )
        image_name = info.get_image(
            key=KUBERNETES_STEP_OPERATOR_DOCKER_IMAGE_KEY
        )
        command = entrypoint_command[:3]
        args = entrypoint_command[3:]

        step_labels = {
            "project_id": kube_utils.sanitize_label_value(
                str(info.snapshot.project_id)
            ),
            "run_id": kube_utils.sanitize_label_value(str(info.run_id)),
            "run_name": kube_utils.sanitize_label_value(str(info.run_name)),
            "pipeline": kube_utils.sanitize_label_value(info.pipeline.name),
            "step_run_id": kube_utils.sanitize_label_value(
                str(info.step_run_id)
            ),
            "step_name": kube_utils.sanitize_label_value(
                info.pipeline_step_name
            ),
        }
        step_annotations = {
            STEP_NAME_ANNOTATION_KEY: info.pipeline_step_name,
            STEP_OPERATOR_ANNOTATION_KEY: str(self.id),
        }

        # We set some default minimum memory resource requests for the step pod
        # here if the user has not specified any, because the step pod takes up
        # some memory resources itself and, if not specified, the pod will be
        # scheduled on any node regardless of available memory and risk
        # negatively impacting or even crashing the node due to memory pressure.
        pod_settings = kube_utils.apply_default_resource_requests(
            memory="400Mi",
            pod_settings=settings.pod_settings,
        )

        pod_manifest = build_pod_manifest(
            pod_name=None,
            image_name=image_name,
            command=command,
            args=args,
            env=environment,
            privileged=settings.privileged,
            pod_settings=pod_settings,
            service_account_name=settings.service_account_name,
            labels=step_labels,
        )

        job_name = settings.job_name_prefix or ""
        random_prefix = "".join(random.choices("0123456789abcdef", k=8))
        job_name += f"-{random_prefix}-{info.pipeline_step_name}-{info.pipeline.name}-step-operator"
        # The job name will be used as a label on the pods, so we need to make
        # sure it doesn't exceed the label length limit
        job_name = kube_utils.sanitize_label(job_name)

        namespace = self.config.kubernetes_namespace
        if settings.node_count > 1:
            environment = {
                **environment,
                **multi_node_environment(
                    job_name=job_name,
                    namespace=namespace,
                    node_count=settings.node_count,
                ),
            }

        if settings.node_count > 1:
            # The gate above guarantees this is a command step. Rank 0
            # runs ZenML's entrypoint (the ONE bookkeeper); other ranks
            # exec the raw command.
            assert info.config.command is not None
            dispatch = build_rank_dispatch_command(
                zenml_entrypoint_command=entrypoint_command,
                raw_command=info.config.command,
            )
            pod_manifest = build_pod_manifest(
                pod_name=None,
                image_name=image_name,
                command=dispatch,
                args=[],
                env=environment,
                privileged=settings.privileged,
                pod_settings=pod_settings,
                service_account_name=settings.service_account_name,
                labels=step_labels,
            )

        job_manifest = build_job_manifest(
            job_name=job_name,
            pod_template=pod_template_manifest_from_pod(pod_manifest),
            # The orchestrator already handles retries, so we don't need to
            # retry the step operator job.
            backoff_limit=0,
            ttl_seconds_after_finished=settings.ttl_seconds_after_finished,
            active_deadline_seconds=settings.active_deadline_seconds,
            labels=step_labels,
            annotations=step_annotations,
        )
        if settings.node_count > 1:
            apply_indexed_completion(job_manifest, settings.node_count)

        kube_utils.create_job(
            batch_api=self._k8s_batch_api,
            namespace=namespace,
            job_manifest=job_manifest,
            api_request_timeout=settings.api_request_timeout,
            max_retries=settings.max_api_retries,
        )

        if settings.node_count > 1:
            # The headless service gives the job's pods stable DNS
            # (rendezvous). Owned by the job so Kubernetes garbage
            # collection reaps it with the job — a crashed or killed
            # client cannot leak the (often GPU-backed) pods.
            created_job = kube_utils.retry_on_api_exception(
                self._k8s_batch_api.read_namespaced_job,
                api_request_timeout=settings.api_request_timeout,
                max_retries=settings.max_api_retries,
            )(name=job_name, namespace=namespace)
            kube_utils.retry_on_api_exception(
                self._k8s_core_api.create_namespaced_service,
                api_request_timeout=settings.api_request_timeout,
                max_retries=settings.max_api_retries,
            )(
                namespace=namespace,
                body=build_headless_service_manifest(created_job),
            )

    def get_status(self, step_run: "StepRunResponse") -> ExecutionStatus:
        """Gets the status of a submitted step.

        Args:
            step_run: The step run.

        Returns:
            The step status.
        """
        label_selector = (
            f"step_run_id={kube_utils.sanitize_label_value(str(step_run.id))}"
        )
        try:
            job_list = kube_utils.list_jobs(
                batch_api=self._k8s_batch_api,
                namespace=self.config.kubernetes_namespace,
                label_selector=label_selector,
                api_request_timeout=self.config.api_request_timeout,
                max_retries=self.config.max_api_retries,
            )
        except Exception as e:
            logger.warning(
                "Failed to list jobs for step run `%s`: %s", step_run.id, e
            )
            return ExecutionStatus.FAILED

        if not job_list.items:
            logger.warning("No jobs found for step run `%s`", step_run.id)
            return ExecutionStatus.FAILED

        job = job_list.items[0]
        if job.status.conditions:
            for condition in job.status.conditions:
                if condition.type == "Complete" and condition.status == "True":
                    return ExecutionStatus.COMPLETED
                if condition.type == "Failed" and condition.status == "True":
                    return ExecutionStatus.FAILED

        return ExecutionStatus.RUNNING

    def cancel(self, step_run: "StepRunResponse") -> None:
        """Cancels a submitted step.

        Args:
            step_run: The step run.
        """
        label_selector = (
            f"step_run_id={kube_utils.sanitize_label_value(str(step_run.id))}"
        )
        try:
            job_list = kube_utils.list_jobs(
                batch_api=self._k8s_batch_api,
                namespace=self.config.kubernetes_namespace,
                label_selector=label_selector,
                api_request_timeout=self.config.api_request_timeout,
                max_retries=self.config.max_api_retries,
            )
        except Exception as e:
            logger.warning(
                "Failed to list jobs for step run `%s`: %s", step_run.id, e
            )
            return

        if not job_list.items:
            logger.warning("No jobs found for step run `%s`", step_run.id)
            return

        job_name = job_list.items[0].metadata.name
        self._k8s_batch_api.delete_namespaced_job(
            name=job_name,
            namespace=self.config.kubernetes_namespace,
            propagation_policy="Foreground",
        )
        logger.info(f"Successfully cancelled step job: {job_name}")
