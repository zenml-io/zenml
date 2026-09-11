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
"""SDK boundary and complete recovery-pagination tests without cloud access."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

pytest.importorskip("nebius")

from grpc import StatusCode
from nebius.aio.service_error import RequestError, RequestStatusExtended
from nebius.api.nebius.ai.v1 import Job, JobSpec, JobStatus, ListJobsResponse
from nebius.api.nebius.common.v1 import ResourceMetadata

from zenml.integrations.nebius import job_client
from zenml.integrations.nebius.submission import SubmissionReceipt


def saved_receipt():
    return SubmissionReceipt(
        component_id="component",
        step_run_id="step",
        pipeline_run_id="run",
        project_id="project",
        subnet_id="subnet",
        submission_id="submission",
        name="nonunique",
        image="image",
        fingerprint="fingerprint",
        created_at=1,
        deadline=100,
        provisioning_deadline=50,
        request_timeout=5,
        poll_interval=1,
        cancel_timeout=2,
        publication_grace=2,
    )


def candidate(job_id, **labels):
    return Job(
        metadata=ResourceMetadata(
            id=job_id,
            parent_id="project",
            name="nonunique",
            labels={
                "zenml-submission": "submission",
                "zenml-step": "step",
                "zenml-fingerprint": "fingerprint",
                **labels,
            },
        ),
        spec=JobSpec(image="image", subnet_id="subnet"),
        status=JobStatus(state=JobStatus.State.RUNNING),
    )


@pytest.fixture
def boundary(monkeypatch):
    service = Mock()
    monkeypatch.setattr(job_client, "JobServiceClient", lambda sdk: service)
    return job_client.JobClient(Mock(), timeout=5), service


def test_create_and_cancel_disable_mutation_retries_and_preserve_key(boundary):
    client, service = boundary
    operation = SimpleNamespace(id="operation", resource_id="job")
    service.create.return_value.wait.return_value = operation
    acknowledged = Mock()
    request = Mock()
    assert client.create(request, "saved-key", acknowledged) == "job"
    acknowledged.assert_called_once_with("operation", "job")
    options = service.create.call_args.kwargs
    assert options["retries"] == 0
    assert options["metadata"] == [("x-idempotency-key", "saved-key")]
    assert options["timeout"] == options["auth_timeout"] == 5
    client.cancel("job", "cancel-key")
    assert service.cancel.call_args.kwargs["retries"] == 0
    assert service.cancel.call_args.kwargs["metadata"] == [
        ("x-idempotency-key", "cancel-key")
    ]
    assert service.cancel.call_args.args[0].id == "job"


def test_operation_identity_is_published_before_wait_failure(boundary):
    client, service = boundary
    operation = Mock(id="operation", resource_id="")
    operation.sync_wait.side_effect = TimeoutError
    service.create.return_value.wait.return_value = operation
    acknowledged = Mock()
    with pytest.raises(TimeoutError):
        client.create(Mock(), "key", acknowledged)
    acknowledged.assert_called_once_with("operation", "")
    assert service.create.call_count == 1


def test_all_pages_return_all_matches_not_first_nonunique_name(boundary):
    client, service = boundary
    service.list.return_value.wait.side_effect = [
        ListJobsResponse(
            items=[
                candidate("first"),
                candidate("unrelated", **{"zenml-step": "different"}),
            ],
            next_page_token="page2",
        ),
        ListJobsResponse(items=[candidate("second")]),
    ]
    assert client.find_candidates(saved_receipt()) == ["first", "second"]
    assert service.list.call_count == 2
    assert service.list.call_args.args[0].page_token == "page2"
    service.create.assert_not_called()
    service.cancel.assert_not_called()


def test_repeated_token_never_returns_partial_recovery_results(boundary):
    client, service = boundary
    service.list.return_value.wait.return_value = ListJobsResponse(
        items=[candidate("job")], next_page_token="same"
    )
    with pytest.raises(RuntimeError, match="incomplete"):
        client.find_candidates(saved_receipt())
    assert service.list.call_count == 2


def test_read_does_not_request_secret_view(boundary):
    client, service = boundary
    client.get("job")
    request = service.get.call_args.args[0]
    assert request.id == "job"
    assert request.view == request.View.VIEW_UNSPECIFIED


def test_sdk_is_closed_even_if_caller_fails(monkeypatch):
    sdk = Mock()
    monkeypatch.setattr(job_client, "SDK", lambda **kwargs: sdk)
    monkeypatch.setattr(job_client, "JobServiceClient", Mock())
    with pytest.raises(ValueError):
        with job_client.connect(SimpleNamespace(credentials_file=None), 5):
            raise ValueError("application failure")
    sdk.sync_close.assert_called_once_with(timeout=5)


@pytest.mark.parametrize(
    "request_id",
    ["11111111-2222-4333-8444-555555555555", "sensitive-invalid-id"],
)
def test_submission_diagnostics_exclude_server_messages(request_id):
    error = RequestError(
        RequestStatusExtended(
            code=StatusCode.PERMISSION_DENIED,
            message="sensitive-server-message",
            details=[],
            service_errors=[],
            request_id=request_id,
            trace_id="sensitive-trace-value",
        )
    )
    metadata = job_client.get_request_error_metadata(error)
    assert metadata["submission_error_code"] == "PERMISSION_DENIED"
    assert ("submission_request_id" in metadata) == (
        request_id.startswith("11111111")
    )
    assert "sensitive" not in repr(metadata)


def test_non_sdk_error_has_no_submission_diagnostics():
    assert job_client.get_request_error_metadata(ValueError("sensitive")) == {}
