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
"""Unit tests for serving capture policies."""

import os
from unittest import mock

from zenml.deployers.serving.policy import (
    ArtifactCaptureMode,
    CapturePolicy,
    CapturePolicyMode,
    derive_artifacts_from_mode,
    get_endpoint_default_policy,
    redact_fields,
    resolve_effective_policy,
    should_capture_artifacts,
    should_capture_payloads,
    should_create_runs,
    truncate_payload,
)


class TestCapturePolicy:
    """Test the CapturePolicy model."""

    def test_default_policy(self):
        """Test default policy values."""
        policy = CapturePolicy()

        assert policy.mode == CapturePolicyMode.FULL
        assert policy.artifacts == ArtifactCaptureMode.NONE
        assert policy.sample_rate == 0.1
        assert policy.max_bytes == 262144
        assert "password" in policy.redact
        assert "secret" in policy.redact

    def test_policy_validation(self):
        """Test policy field validation."""
        # Valid policy
        policy = CapturePolicy(
            mode=CapturePolicyMode.FULL,
            artifacts=ArtifactCaptureMode.SAMPLED,
            sample_rate=0.5,
            max_bytes=1024,
            redact=["custom_field"],
        )
        assert policy.mode == CapturePolicyMode.FULL
        assert policy.artifacts == ArtifactCaptureMode.SAMPLED
        assert policy.sample_rate == 0.5
        assert policy.max_bytes == 1024
        assert policy.redact == ["custom_field"]

    def test_redact_normalization(self):
        """Test that redact fields are normalized to lowercase."""
        policy = CapturePolicy(redact=["PASSWORD", "Token", "SECRET"])
        assert policy.redact == ["password", "token", "secret"]

    def test_derive_artifacts_from_mode(self):
        """Test derive_artifacts_from_mode function."""
        # Test all mode mappings
        assert (
            derive_artifacts_from_mode(CapturePolicyMode.FULL)
            == ArtifactCaptureMode.FULL
        )
        assert (
            derive_artifacts_from_mode(CapturePolicyMode.SAMPLED)
            == ArtifactCaptureMode.SAMPLED
        )
        assert (
            derive_artifacts_from_mode(CapturePolicyMode.ERRORS_ONLY)
            == ArtifactCaptureMode.ERRORS_ONLY
        )
        assert (
            derive_artifacts_from_mode(CapturePolicyMode.METADATA)
            == ArtifactCaptureMode.NONE
        )
        assert (
            derive_artifacts_from_mode(CapturePolicyMode.NONE)
            == ArtifactCaptureMode.NONE
        )


class TestPolicyFunctions:
    """Test policy utility functions."""

    def test_should_create_runs(self):
        """Test should_create_runs function."""
        assert not should_create_runs(
            CapturePolicy(mode=CapturePolicyMode.NONE)
        )
        assert should_create_runs(
            CapturePolicy(mode=CapturePolicyMode.METADATA)
        )
        assert should_create_runs(CapturePolicy(mode=CapturePolicyMode.FULL))

    def test_should_capture_payloads(self):
        """Test should_capture_payloads function."""
        assert not should_capture_payloads(
            CapturePolicy(mode=CapturePolicyMode.NONE)
        )
        assert not should_capture_payloads(
            CapturePolicy(mode=CapturePolicyMode.METADATA)
        )
        assert not should_capture_payloads(
            CapturePolicy(mode=CapturePolicyMode.ERRORS_ONLY)
        )
        assert should_capture_payloads(
            CapturePolicy(mode=CapturePolicyMode.SAMPLED)
        )
        assert should_capture_payloads(
            CapturePolicy(mode=CapturePolicyMode.FULL)
        )

    def test_should_capture_artifacts(self):
        """Test should_capture_artifacts function."""
        # No artifacts mode
        policy = CapturePolicy(artifacts=ArtifactCaptureMode.NONE)
        assert not should_capture_artifacts(policy, is_error=False)
        assert not should_capture_artifacts(policy, is_error=True)

        # Errors only mode
        policy = CapturePolicy(artifacts=ArtifactCaptureMode.ERRORS_ONLY)
        assert not should_capture_artifacts(policy, is_error=False)
        assert should_capture_artifacts(policy, is_error=True)

        # Full mode
        policy = CapturePolicy(artifacts=ArtifactCaptureMode.FULL)
        assert should_capture_artifacts(policy, is_error=False)
        assert should_capture_artifacts(policy, is_error=True)

        # Sampled mode
        policy = CapturePolicy(artifacts=ArtifactCaptureMode.SAMPLED)
        assert should_capture_artifacts(policy, is_error=False)
        assert should_capture_artifacts(policy, is_error=True)


class TestRedactionAndTruncation:
    """Test redaction and truncation utilities."""

    def test_redact_fields_simple(self):
        """Test basic field redaction."""
        data = {
            "username": "alice",
            "password": "secret123",
            "email": "alice@example.com",
        }
        redact_list = ["password"]

        result = redact_fields(data, redact_list)

        assert result["username"] == "alice"
        assert result["password"] == "[REDACTED]"
        assert result["email"] == "alice@example.com"

    def test_redact_fields_case_insensitive(self):
        """Test case-insensitive redaction."""
        data = {
            "user_PASSWORD": "secret123",
            "api_Key": "abc123",
            "auth_token": "xyz789",
        }
        redact_list = ["password", "key", "token"]

        result = redact_fields(data, redact_list)

        assert result["user_PASSWORD"] == "[REDACTED]"
        assert result["api_Key"] == "[REDACTED]"
        assert result["auth_token"] == "[REDACTED]"

    def test_redact_fields_nested(self):
        """Test redaction of nested dictionaries."""
        data = {
            "config": {
                "database": {"password": "db_secret"},
                "api_key": "api_secret",
            },
            "username": "alice",
        }
        redact_list = ["password", "key"]

        result = redact_fields(data, redact_list)

        assert result["config"]["database"]["password"] == "[REDACTED]"
        assert result["config"]["api_key"] == "[REDACTED]"
        assert result["username"] == "alice"

    def test_redact_fields_empty_list(self):
        """Test redaction with empty redact list."""
        data = {"password": "secret", "username": "alice"}
        result = redact_fields(data, [])
        assert result == data

    def test_truncate_payload_json(self):
        """Test payload truncation for JSON-serializable data."""
        data = {"key": "a" * 1000}  # Large string
        max_bytes = 100

        result = truncate_payload(data, max_bytes)

        assert len(result.encode("utf-8")) <= max_bytes
        assert "TRUNCATED" in result

    def test_truncate_payload_small(self):
        """Test payload truncation for small data."""
        data = {"key": "small_value"}
        max_bytes = 1000

        result = truncate_payload(data, max_bytes)

        assert "TRUNCATED" not in result
        assert "small_value" in result

    def test_truncate_payload_non_json(self):
        """Test payload truncation for non-JSON data."""

        class NonSerializable:
            def __str__(self):
                return "a" * 1000

        data = NonSerializable()
        max_bytes = 100

        result = truncate_payload(data, max_bytes)

        assert len(result.encode("utf-8")) <= max_bytes
        assert "TRUNCATED" in result


class TestEnvironmentConfiguration:
    """Test environment-based policy configuration."""

    @mock.patch.dict(os.environ, {}, clear=True)
    def test_default_environment_policy(self):
        """Test default policy from environment."""
        policy = get_endpoint_default_policy()

        assert policy.mode == CapturePolicyMode.FULL
        assert policy.artifacts == ArtifactCaptureMode.NONE
        assert policy.sample_rate == 0.1
        assert policy.max_bytes == 262144

    @mock.patch.dict(
        os.environ,
        {
            "ZENML_SERVING_CAPTURE_DEFAULT": "full",
            "ZENML_SERVING_CAPTURE_ARTIFACTS": "sampled",
            "ZENML_SERVING_CAPTURE_SAMPLE_RATE": "0.5",
            "ZENML_SERVING_CAPTURE_MAX_BYTES": "1024",
            "ZENML_SERVING_CAPTURE_REDACT": "custom_field,another_field",
        },
    )
    def test_custom_environment_policy(self):
        """Test custom policy from environment variables."""
        policy = get_endpoint_default_policy()

        assert policy.mode == CapturePolicyMode.FULL
        assert policy.artifacts == ArtifactCaptureMode.SAMPLED
        assert policy.sample_rate == 0.5
        assert policy.max_bytes == 1024
        assert "custom_field" in policy.redact
        assert "another_field" in policy.redact

    @mock.patch.dict(
        os.environ,
        {
            "ZENML_SERVING_CAPTURE_DEFAULT": "invalid_mode",
            "ZENML_SERVING_CAPTURE_ARTIFACTS": "invalid_artifacts",
            "ZENML_SERVING_CAPTURE_SAMPLE_RATE": "1.5",  # Out of range
            "ZENML_SERVING_CAPTURE_MAX_BYTES": "100",  # Too small
        },
    )
    def test_invalid_environment_values(self):
        """Test handling of invalid environment values."""
        policy = get_endpoint_default_policy()

        # Should fall back to defaults for invalid values
        assert policy.mode == CapturePolicyMode.FULL
        assert policy.artifacts == ArtifactCaptureMode.NONE
        # Should clamp to valid ranges
        assert policy.sample_rate == 1.0  # Clamped to max
        assert policy.max_bytes == 1024  # Clamped to min


class TestPolicyResolution:
    """Test policy resolution with precedence."""

    def test_resolve_policy_no_overrides(self):
        """Test policy resolution with no overrides."""
        endpoint_default = CapturePolicy(mode=CapturePolicyMode.METADATA)

        result = resolve_effective_policy(endpoint_default)

        assert result.mode == CapturePolicyMode.METADATA

    def test_resolve_policy_request_override(self):
        """Test policy resolution with request override."""
        endpoint_default = CapturePolicy(mode=CapturePolicyMode.METADATA)
        request_override = {"mode": "full", "sample_rate": 0.8}

        result = resolve_effective_policy(
            endpoint_default, request_override=request_override
        )

        assert result.mode == CapturePolicyMode.FULL
        assert result.sample_rate == 0.8

    def test_resolve_policy_code_override(self):
        """Test policy resolution with code override."""
        endpoint_default = CapturePolicy(mode=CapturePolicyMode.METADATA)
        code_override = {"artifacts": "full"}

        result = resolve_effective_policy(
            endpoint_default, code_override=code_override
        )

        assert result.mode == CapturePolicyMode.METADATA
        assert result.artifacts == ArtifactCaptureMode.FULL

    def test_resolve_policy_precedence(self):
        """Test policy resolution precedence (request > code > endpoint)."""
        endpoint_default = CapturePolicy(
            mode=CapturePolicyMode.METADATA, sample_rate=0.1
        )
        code_override = {"mode": "sampled", "sample_rate": 0.3}
        request_override = {"sample_rate": 0.8}

        result = resolve_effective_policy(
            endpoint_default,
            request_override=request_override,
            code_override=code_override,
        )

        # Request override takes precedence for sample_rate
        assert result.sample_rate == 0.8
        # Code override takes precedence for mode (not overridden by request)
        assert result.mode == CapturePolicyMode.SAMPLED

    def test_resolve_policy_invalid_keys(self):
        """Test policy resolution ignores invalid override keys."""
        endpoint_default = CapturePolicy(mode=CapturePolicyMode.METADATA)
        request_override = {
            "mode": "full",
            "invalid_key": "should_be_ignored",
            "another_invalid": True,
        }

        result = resolve_effective_policy(
            endpoint_default, request_override=request_override
        )

        assert result.mode == CapturePolicyMode.FULL
        # Invalid keys should be ignored, no exception raised
        assert not hasattr(result, "invalid_key")

    def test_resolve_policy_derives_artifacts_from_mode(self):
        """Test that resolve_effective_policy derives artifacts from mode when not explicitly set."""
        endpoint_default = CapturePolicy()

        # Test with mode=full, no explicit artifacts override
        resolved = resolve_effective_policy(
            endpoint_default=endpoint_default,
            request_override={"mode": "full"},
        )
        assert resolved.mode == CapturePolicyMode.FULL
        assert (
            resolved.artifacts == ArtifactCaptureMode.FULL
        )  # Derived from mode

        # Test with mode=sampled, no explicit artifacts override
        resolved = resolve_effective_policy(
            endpoint_default=endpoint_default,
            request_override={"mode": "sampled"},
        )
        assert resolved.mode == CapturePolicyMode.SAMPLED
        assert (
            resolved.artifacts == ArtifactCaptureMode.SAMPLED
        )  # Derived from mode

        # Test with explicit artifacts override (should not derive)
        resolved = resolve_effective_policy(
            endpoint_default=endpoint_default,
            request_override={"mode": "full", "artifacts": "none"},
        )
        assert resolved.mode == CapturePolicyMode.FULL
        assert (
            resolved.artifacts == ArtifactCaptureMode.NONE
        )  # Explicit override, not derived


class TestPrecedenceRules:
    """Test precedence rules for capture policies."""

    def test_global_mode_precedence(self):
        """Test global mode precedence: Step > Request > Pipeline > Default."""
        endpoint_default = CapturePolicy(
            mode=CapturePolicyMode.FULL
        )  # Default

        # Request overrides pipeline and default
        resolved = resolve_effective_policy(
            endpoint_default=endpoint_default,
            request_override={"mode": "metadata"},
            code_override={"mode": "sampled"},  # Pipeline level
        )
        assert resolved.mode == CapturePolicyMode.METADATA  # Request wins

        # Without request override, pipeline wins
        resolved = resolve_effective_policy(
            endpoint_default=endpoint_default,
            code_override={"mode": "sampled"},  # Pipeline level
        )
        assert (
            resolved.mode == CapturePolicyMode.SAMPLED
        )  # Pipeline wins over default

    def test_artifacts_derived_from_final_mode(self):
        """Test that artifacts are derived from the final resolved mode."""
        endpoint_default = CapturePolicy(mode=CapturePolicyMode.FULL)

        # Mode is overridden, artifacts should be derived from final mode
        resolved = resolve_effective_policy(
            endpoint_default=endpoint_default,
            request_override={"mode": "metadata"},
        )
        assert resolved.mode == CapturePolicyMode.METADATA
        assert (
            resolved.artifacts == ArtifactCaptureMode.NONE
        )  # Derived from metadata

        # Test sampled mode derivation
        resolved = resolve_effective_policy(
            endpoint_default=endpoint_default,
            request_override={"mode": "sampled"},
        )
        assert resolved.mode == CapturePolicyMode.SAMPLED
        assert (
            resolved.artifacts == ArtifactCaptureMode.SAMPLED
        )  # Derived from sampled

    def test_artifacts_override_prevents_derivation(self):
        """Test that explicit artifacts override prevents derivation."""
        endpoint_default = CapturePolicy(mode=CapturePolicyMode.FULL)

        # Explicit artifacts override should not be derived
        resolved = resolve_effective_policy(
            endpoint_default=endpoint_default,
            request_override={"mode": "sampled", "artifacts": "full"},
        )
        assert resolved.mode == CapturePolicyMode.SAMPLED
        assert (
            resolved.artifacts == ArtifactCaptureMode.FULL
        )  # Explicit, not derived
