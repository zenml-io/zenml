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
"""Storage of large execution payloads outside of their SQL columns.

Snapshots, step runs and runs keep configurations, environments and source
code in payload columns. With offloading enabled, these values are stored as
content-addressed blobs in a payload backend, and the rows only reference
them. The store resolves the references when it builds responses that carry
payloads.
"""

from zenml.zen_stores.payload_storage.config import (
    PayloadBackendType,
    PayloadStorageConfiguration,
)
from zenml.zen_stores.payload_storage.payloads import (
    UNRESOLVED,
    PayloadField,
    PayloadSchema,
    PayloadValue,
    ReadsPayloads,
    ResolvedPayloads,
    UnconfiguredPayloads,
    UnresolvedPayloadError,
    get_blob_ids,
    get_inline_payloads,
    read_payload,
)

__all__ = [
    "UNRESOLVED",
    "PayloadBackendType",
    "PayloadField",
    "PayloadSchema",
    "PayloadStorageConfiguration",
    "PayloadValue",
    "ReadsPayloads",
    "ResolvedPayloads",
    "UnconfiguredPayloads",
    "UnresolvedPayloadError",
    "get_blob_ids",
    "get_inline_payloads",
    "read_payload",
]
