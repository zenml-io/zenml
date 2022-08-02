#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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

from zenml.integrations.label_studio.label_studio_utils import (
    get_file_extension,
    is_azure_url,
    is_gcs_url,
    is_s3_url,
)


def test_is_s3_url():
    s3_url = "https://s3.amazonaws.com/zenml-test-bucket/test_file.txt"
    not_s3_url = "https://www.aria.com"
    assert is_s3_url(s3_url)
    assert not is_s3_url(not_s3_url)


def test_is_azure_url():
    azure_url = "https://zenml-test-bucket.blob.core.windows.net/test_file.txt"
    not_azure_url = "https://www.aria.com"
    assert is_azure_url(azure_url)
    assert not is_azure_url(not_azure_url)


def test_is_gcs_url():
    gcs_url = "https://zenml-test-bucket.storage.googleapis.com/test_file.txt"
    not_gcs_url = "https://www.aria.com"
    assert is_gcs_url(gcs_url)
    assert not is_gcs_url(not_gcs_url)


def test_getting_file_extension():
    file_extension = ".txt"
    file_name = "test_file.txt"
    assert get_file_extension(file_name) == file_extension

    file_name = "test_file"
    assert get_file_extension(file_name) == ""

    file_name = "test_file."
    assert get_file_extension(file_name) == "."

    file_name = "test_file.tar.gz"
    assert get_file_extension(file_name) == ".gz"
