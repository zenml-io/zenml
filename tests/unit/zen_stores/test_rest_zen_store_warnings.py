#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""Tests for REST ZenStore version mismatch warnings."""

import tempfile
import unittest.mock as mock
from pathlib import Path
from unittest import TestCase


class TestVersionMismatchWarning(TestCase):
    """Test that version mismatch warning is shown only once per session."""

    def test_version_mismatch_warning_session_tracking(self):
        """Test that the warning is shown only once per session."""
        # Import the module to access the functions
        from zenml.zen_stores import rest_zen_store

        # Create a temporary directory for this test
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock the temp directory to use our test directory
            mock_temp_file = Path(temp_dir) / "zenml_version_warning_test.tmp"

            with mock.patch.object(
                rest_zen_store,
                "_get_session_warning_file",
                return_value=mock_temp_file,
            ):
                # Mock the logger to capture warnings
                with mock.patch.object(
                    rest_zen_store, "logger"
                ) as mock_logger:
                    # Mock the DISABLE_CLIENT_SERVER_MISMATCH_WARNING constant
                    with mock.patch.object(
                        rest_zen_store,
                        "DISABLE_CLIENT_SERVER_MISMATCH_WARNING",
                        False,
                    ):
                        # Mock zenml.__version__ to return different version
                        with mock.patch("zenml.__version__", "0.84.0"):
                            # Simulate the version mismatch check logic
                            server_version = "0.83.1"
                            client_version = "0.84.0"

                            # First call should show warning
                            if (
                                not rest_zen_store.DISABLE_CLIENT_SERVER_MISMATCH_WARNING
                                and (server_version != client_version)
                            ):
                                if not rest_zen_store._has_warning_been_shown():
                                    rest_zen_store.logger.warning(
                                        "Your ZenML client version (%s) does not match the server "
                                        "version (%s). This version mismatch might lead to errors or "
                                        "unexpected behavior. \nTo disable this warning message, set "
                                        "the environment variable `%s=True`",
                                        client_version,
                                        server_version,
                                        rest_zen_store.ENV_ZENML_DISABLE_CLIENT_SERVER_MISMATCH_WARNING,
                                    )
                                    rest_zen_store._mark_warning_as_shown()

                            # Second call should not show warning
                            if (
                                not rest_zen_store.DISABLE_CLIENT_SERVER_MISMATCH_WARNING
                                and (server_version != client_version)
                            ):
                                if not rest_zen_store._has_warning_been_shown():
                                    rest_zen_store.logger.warning(
                                        "Your ZenML client version (%s) does not match the server "
                                        "version (%s). This version mismatch might lead to errors or "
                                        "unexpected behavior. \nTo disable this warning message, set "
                                        "the environment variable `%s=True`",
                                        client_version,
                                        server_version,
                                        rest_zen_store.ENV_ZENML_DISABLE_CLIENT_SERVER_MISMATCH_WARNING,
                                    )
                                    rest_zen_store._mark_warning_as_shown()

                            # Assert that warning was called only once
                            self.assertEqual(mock_logger.warning.call_count, 1)

                            # Assert that the warning file was created
                            self.assertTrue(mock_temp_file.exists())

    def test_has_warning_been_shown_functions(self):
        """Test the helper functions for warning tracking."""
        from zenml.zen_stores import rest_zen_store

        # Create a temporary directory for this test
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock the temp directory to use our test directory
            mock_temp_file = Path(temp_dir) / "zenml_version_warning_test.tmp"

            with mock.patch.object(
                rest_zen_store,
                "_get_session_warning_file",
                return_value=mock_temp_file,
            ):
                # Initially, warning should not be shown
                self.assertFalse(rest_zen_store._has_warning_been_shown())

                # Mark warning as shown
                rest_zen_store._mark_warning_as_shown()

                # Now warning should be shown
                self.assertTrue(rest_zen_store._has_warning_been_shown())

                # File should exist
                self.assertTrue(mock_temp_file.exists())
