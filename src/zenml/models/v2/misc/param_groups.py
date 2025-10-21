#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Parameter group classes."""

from uuid import UUID

from pydantic import BaseModel, model_validator


class VersionedIdentifier(BaseModel):
    """Class grouping identifiers for entities resolved by UUID or name&version."""

    id: UUID | None = None
    name: str | None = None
    version: str | None = None

    @model_validator(mode="after")
    def _validate_options(self) -> "VersionedIdentifier":
        if self.id and self.name:
            raise ValueError(
                "You can use only identification option at a time."
                "Use either id or name."
            )

        if not (self.id or self.name):
            raise ValueError(
                "You have to use at least one identification option."
                "Use either id or name."
            )

        if bool(self.name) ^ bool(self.version):
            raise ValueError("You need to specify both name and version.")

        return self


class ArtifactVersionIdentifier(VersionedIdentifier):
    """Class for artifact version identifier group."""

    pass


class ModelVersionIdentifier(VersionedIdentifier):
    """Class for model version identifier group."""

    pass


class PipelineRunIdentifier(BaseModel):
    """Class grouping different pipeline run identifiers."""

    id: UUID | None = None
    name: str | None = None
    prefix: str | None = None

    @property
    def value(self) -> str | UUID:
        """Resolves the set value out of id, name, prefix etc.

        Returns:
            The id/name/prefix (if set, in this exact order).
        """
        return self.id or self.name or self.prefix  # type: ignore[return-value]

    @model_validator(mode="after")
    def _validate_options(self) -> "PipelineRunIdentifier":
        options = [
            bool(self.id),
            bool(self.name),
            bool(self.prefix),
        ]

        if sum(options) > 1:
            raise ValueError(
                "You can use only identification option at a time."
                "Use either id or name or prefix."
            )

        if sum(options) == 0:
            raise ValueError(
                "You have to use at least one identification option."
                "Use either id or name or prefix."
            )

        return self


class StepRunIdentifier(BaseModel):
    """Class grouping different step run identifiers."""

    id: UUID | None = None
    name: str | None = None
    run: PipelineRunIdentifier | None = None

    @model_validator(mode="after")
    def _validate_options(self) -> "StepRunIdentifier":
        if self.id and self.name:
            raise ValueError(
                "You can use only identification option at a time."
                "Use either id or name."
            )

        if not (self.id or self.name):
            raise ValueError(
                "You have to use at least one identification option."
                "Use either id or name."
            )

        if bool(self.name) ^ bool(self.run):
            raise ValueError(
                "To identify a step run by name you need to specify a pipeline run identifier."
            )

        return self
