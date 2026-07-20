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
"""Unit tests for the Kubernetes pod service."""

from unittest import mock
from uuid import UUID

import pytest
from kubernetes import client as k8s_client
from kubernetes.client.rest import ApiException

from zenml.enums import ServiceState
from zenml.integrations.kubernetes.services import (
    kubernetes_pod_service as kps,
)
from zenml.integrations.kubernetes.services.kubernetes_pod_service import (
    TTL_SECONDS_AFTER_FINISHED,
    KubernetesPodService,
    KubernetesPodServiceConfig,
    build_pod_service_manifest,
    build_service_job_manifest,
    pod_is_ready,
)

_UUID = UUID("00000000-0000-0000-0000-0000000000ab")


def _service(
    name: str = "test-svc", **config_overrides: object
) -> KubernetesPodService:
    """Build a service instance with a fixed uuid for deterministic names.

    Args:
        name: The service config name.
        **config_overrides: Overrides for the service config.

    Returns:
        The service instance.
    """
    config = KubernetesPodServiceConfig(
        name=name,
        image="my-image:latest",
        command=["run", "server"],
        port=8080,
        **config_overrides,
    )
    return KubernetesPodService(uuid=_UUID, config=config)


def _job(
    name: str = "zenml-svc-00000000", uid: str = "uid-1"
) -> k8s_client.V1Job:
    """Build a minimal job manifest.

    Args:
        name: The job name.
        uid: The job uid.

    Returns:
        The job manifest.
    """
    return k8s_client.V1Job(
        metadata=k8s_client.V1ObjectMeta(
            name=name, uid=uid, labels={"zenml-service-uuid": "abc"}
        )
    )


def _pod(
    phase: str,
    ready: bool | None = None,
    reason: str | None = None,
) -> k8s_client.V1Pod:
    """Build a pod with the given phase/readiness.

    Args:
        phase: The pod phase.
        ready: Whether the pod's `Ready` condition is true. Omitted if None.
        reason: The pod status reason.

    Returns:
        The pod manifest.
    """
    conditions = None
    if ready is not None:
        conditions = [
            k8s_client.V1PodCondition(
                type="Ready", status="True" if ready else "False"
            )
        ]
    return k8s_client.V1Pod(
        metadata=k8s_client.V1ObjectMeta(name="pod-x"),
        status=k8s_client.V1PodStatus(
            phase=phase, reason=reason, conditions=conditions
        ),
    )


class TestManifests:
    def test_job_manifest_has_gc_backstops(self) -> None:
        job = build_service_job_manifest(
            job_name="zenml-svc-abc",
            pod_template=k8s_client.V1PodTemplateSpec(
                spec=k8s_client.V1PodSpec(containers=[])
            ),
            max_lifetime_seconds=3600,
            labels={"a": "b"},
        )
        # The whole point of the service: Kubernetes reaps it on its own.
        assert job.spec.backoff_limit == 0
        assert job.spec.active_deadline_seconds == 3600
        assert (
            job.spec.ttl_seconds_after_finished == TTL_SECONDS_AFTER_FINISHED
        )

    def test_service_owned_by_job(self) -> None:
        service = build_pod_service_manifest(_job(), port=8080)
        assert service.spec.cluster_ip == "None"
        assert service.spec.selector == {"job-name": "zenml-svc-00000000"}
        assert service.spec.publish_not_ready_addresses is True
        assert service.spec.ports[0].port == 8080
        owner = service.metadata.owner_references[0]
        assert owner.kind == "Job"
        assert owner.name == "zenml-svc-00000000"
        assert owner.uid == "uid-1"


class TestProvision:
    def test_provision_creates_owned_resources(self) -> None:
        service = _service(max_lifetime_seconds=1234)
        name = service._resource_name

        with (
            mock.patch.object(KubernetesPodService, "_batch_api"),
            mock.patch.object(KubernetesPodService, "_core_api") as core_api,
            mock.patch.object(kps.kube_utils, "create_job") as create_job,
            mock.patch.object(kps.kube_utils, "get_job") as get_job,
        ):
            get_job.return_value = _job(name=name, uid="uid-9")
            service.provision()

            job_manifest = create_job.call_args.kwargs["job_manifest"]
            assert job_manifest.spec.backoff_limit == 0
            assert job_manifest.spec.active_deadline_seconds == 1234
            assert (
                job_manifest.spec.ttl_seconds_after_finished
                == TTL_SECONDS_AFTER_FINISHED
            )
            # Stable per-pod DNS comes from hostname + subdomain.
            pod_spec = job_manifest.spec.template.spec
            assert pod_spec.hostname == name
            assert pod_spec.subdomain == name

            service_body = core_api.return_value.create_namespaced_service.call_args.kwargs[
                "body"
            ]
            assert service_body.metadata.owner_references[0].uid == "uid-9"
            assert service_body.spec.ports[0].port == 8080

        # The endpoint exposes the in-cluster URL.
        assert service.endpoint is not None
        assert service.endpoint.status.uri == service.url

    def test_url_property(self) -> None:
        service = _service()
        name = service._resource_name
        assert service.url == f"http://{name}.{name}.default.svc:8080"


class TestResourceName:
    def test_named_service_has_stable_url_before_provisioning(self) -> None:
        """A named service's URL is derived from the name, not the uuid."""
        service = _service(name="my-policy")
        assert service._resource_name == "zenml-svc-my-policy"
        assert (
            service.url
            == "http://zenml-svc-my-policy.zenml-svc-my-policy.default.svc:8080"
        )

    def test_unnamed_service_falls_back_to_uuid(self) -> None:
        """Without a name, resource names derive from the service uuid.

        `BaseService.__init__` fills a blank name with the class name, so
        leaving `name` unset (here via a `model_name`-only config) is what
        "unnamed" means in practice.
        """
        config = KubernetesPodServiceConfig(
            model_name="policy",
            image="my-image:latest",
            command=["run", "server"],
            port=8080,
        )
        service = KubernetesPodService(uuid=_UUID, config=config)
        assert service._resource_name == "zenml-svc-00000000"

    def test_name_is_sanitized_to_a_dns_label(self) -> None:
        """Uppercase and underscores are folded to a DNS-1123 label."""
        service = _service(name="My_Policy--Server")
        assert service._resource_name == "zenml-svc-my-policy-server"

    def test_overlong_name_is_trimmed_to_63_chars(self) -> None:
        """The resource name never exceeds the 63-char DNS label limit."""
        service = _service(name="a" * 100)
        name = service._resource_name
        assert len(name) <= 63
        assert name.startswith("zenml-svc-")
        assert not name.endswith("-")


class TestCheckStatus:
    @pytest.mark.parametrize(
        "pod, expected_state",
        [
            (_pod("Pending"), ServiceState.PENDING_STARTUP),
            (_pod("Running", ready=True), ServiceState.ACTIVE),
            (_pod("Running", ready=False), ServiceState.PENDING_STARTUP),
            (_pod("Failed"), ServiceState.ERROR),
            (_pod("Succeeded"), ServiceState.INACTIVE),
        ],
    )
    def test_phase_mapping(
        self, pod: k8s_client.V1Pod, expected_state: ServiceState
    ) -> None:
        service = _service()
        with mock.patch.object(
            KubernetesPodService, "_get_service_pod", return_value=pod
        ):
            state, _ = service.check_status()
        assert state == expected_state

    def test_missing_pod_is_inactive(self) -> None:
        service = _service()
        with mock.patch.object(
            KubernetesPodService, "_get_service_pod", return_value=None
        ):
            state, message = service.check_status()
        assert state == ServiceState.INACTIVE
        assert "No pod" in message


class TestDeprovision:
    def test_missing_job_swallowed(self) -> None:
        service = _service()
        batch_api = mock.Mock()
        batch_api.delete_namespaced_job = mock.Mock(
            side_effect=ApiException(status=404)
        )
        with mock.patch.object(
            KubernetesPodService, "_batch_api", return_value=batch_api
        ):
            service.deprovision()
        batch_api.delete_namespaced_job.assert_called_once()

    def test_other_error_reraised(self) -> None:
        service = _service()
        batch_api = mock.Mock()
        batch_api.delete_namespaced_job = mock.Mock(
            side_effect=ApiException(status=500)
        )
        with mock.patch.object(
            KubernetesPodService, "_batch_api", return_value=batch_api
        ):
            with pytest.raises(ApiException):
                service.deprovision()


class TestPodReadiness:
    def test_ready_condition_true(self) -> None:
        assert pod_is_ready(_pod("Running", ready=True)) is True

    def test_ready_condition_false(self) -> None:
        assert pod_is_ready(_pod("Running", ready=False)) is False

    def test_no_conditions(self) -> None:
        assert pod_is_ready(_pod("Running")) is False
