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
import pydantic
import pytest

from zenml.metadata_stores import SQLiteMetadataStore


def test_sqlite_metadata_store_only_supports_local_uris():
    """Checks that a sqlite metadata store can only be initialized with a local
    uri."""
    with pytest.raises(pydantic.ValidationError):
        SQLiteMetadataStore(uri="gs://remote/uri")

    with pytest.raises(pydantic.ValidationError):
        SQLiteMetadataStore(uri="s3://remote/uri")

    with pytest.raises(pydantic.ValidationError):
        SQLiteMetadataStore(uri="hdfs://remote/uri")

    metadata_store = SQLiteMetadataStore(uri="/local/uri")
    assert metadata_store.uri == "/local/uri"
