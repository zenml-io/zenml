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
"""Materializer for ``ModalSandboxSnapshot``.

Registering a dedicated materializer (rather than relying on the generic
``PydanticMaterializer``) gives the materializer registry a direct binding for
``ModalSandboxSnapshot`` so ``save_artifact(snap)`` resolves to the right
loader without walking the type MRO, and lets the artifact surface in the UI
with its real type name.
"""

from typing import Any, ClassVar, Tuple, Type

from zenml.integrations.modal.sandboxes import ModalSandboxSnapshot
from zenml.materializers.pydantic_materializer import PydanticMaterializer


class ModalSandboxSnapshotMaterializer(PydanticMaterializer):
    """Persists a ``ModalSandboxSnapshot`` as JSON.

    A snapshot is a lightweight Pydantic object — just the Modal Image id
    plus metadata. The underlying Modal Image is stored on Modal's
    infrastructure; this materializer only persists the *reference* to it.
    """

    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (ModalSandboxSnapshot,)
