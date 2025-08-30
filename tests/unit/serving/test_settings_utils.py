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
"""Unit tests for serving settings normalization."""

from zenml.config.serving_settings import ServingCaptureSettings
from zenml.utils.settings_utils import (
    get_pipeline_serving_capture_settings,
    get_step_serving_capture_settings,
    normalize_serving_capture_settings,
)


class TestServingCaptureSettingsNormalization:
    """Test normalization of serving capture settings."""

    def test_normalize_new_format(self):
        """Test normalization of new format settings."""
        settings = {
            "serving_capture": {
                "mode": "full",
                "sample_rate": 0.5,
                "inputs": {"city": "metadata"},
                "outputs": "full",
            }
        }

        result = normalize_serving_capture_settings(settings)

        assert result is not None
        assert isinstance(result, ServingCaptureSettings)
        assert result.mode == "full"
        assert result.sample_rate == 0.5
        assert result.inputs == {"city": "metadata"}
        assert result.outputs == "full"

    def test_normalize_legacy_format(self):
        """Test normalization of legacy format settings."""
        settings = {
            "serving": {
                "capture": {
                    "mode": "sampled",
                    "sample_rate": 0.1,
                    "max_bytes": 1024,
                    "inputs": {
                        "city": {"mode": "full"},
                        "data": {"mode": "metadata"},
                    },
                    "outputs": {"result": {"mode": "sampled"}},
                }
            }
        }

        result = normalize_serving_capture_settings(settings)

        assert result is not None
        assert isinstance(result, ServingCaptureSettings)
        assert result.mode == "sampled"
        assert result.sample_rate == 0.1
        assert result.max_bytes == 1024
        assert result.inputs == {"city": "full", "data": "metadata"}
        assert result.outputs == {"result": "sampled"}

    def test_normalize_legacy_format_string_outputs(self):
        """Test normalization of legacy format with string outputs."""
        settings = {
            "serving": {"capture": {"mode": "full", "outputs": "metadata"}}
        }

        result = normalize_serving_capture_settings(settings)

        assert result is not None
        assert result.outputs == "metadata"

    def test_normalize_no_capture_settings(self):
        """Test normalization when no capture settings present."""
        settings = {
            "docker": {"requirements": ["pandas"]},
            "resources": {"memory": "2GB"},
        }

        result = normalize_serving_capture_settings(settings)

        assert result is None

    def test_normalize_empty_settings(self):
        """Test normalization with empty settings dict."""
        result = normalize_serving_capture_settings({})
        assert result is None

    def test_pipeline_settings_extraction(self):
        """Test pipeline-level settings extraction."""
        settings = {
            "serving_capture": {
                "mode": "metadata",
                "inputs": {"param": "full"},
            }
        }

        result = get_pipeline_serving_capture_settings(settings)

        assert result is not None
        assert result.mode == "metadata"
        assert result.inputs == {"param": "full"}

    def test_step_settings_extraction(self):
        """Test step-level settings extraction."""
        settings = {
            "serving_capture": {
                "inputs": {"data": "none"},
                "outputs": "sampled",
                "sample_rate": 0.2,
            }
        }

        result = get_step_serving_capture_settings(settings)

        assert result is not None
        assert result.inputs == {"data": "none"}
        assert result.outputs == "sampled"
        assert result.sample_rate == 0.2

    def test_precedence_new_over_legacy(self):
        """Test that new format takes precedence over legacy."""
        settings = {
            "serving_capture": {"mode": "full"},
            "serving": {"capture": {"mode": "metadata"}},
        }

        result = normalize_serving_capture_settings(settings)

        assert result is not None
        assert result.mode == "full"  # New format wins
