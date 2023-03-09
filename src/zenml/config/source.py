#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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

from enum import Enum
from typing import Any, Optional, Type, TypeVar
from uuid import UUID

from pydantic import BaseModel, validator

from zenml.logger import get_logger

logger = get_logger(__name__)

S = TypeVar("S", bound="Source")


class SourceType(Enum):
    USER = "user"
    BUILTIN = "builtin"  # TODO: maybe store python version?
    DISTRIBUTION_PACKAGE = "distribution_package"
    CODE_REPOSITORY = "code_repository"
    UNKNOWN = "unknown"


class Source(BaseModel):
    module: str
    attribute: Optional[str] = None
    type: SourceType

    def __new__(cls, **kwargs: Any) -> "Source":
        type_ = kwargs.get("type")
        type_ = SourceType(type_) if type_ else None

        if type_ == SourceType.CODE_REPOSITORY:
            return object.__new__(CodeRepositorySource)
        elif type_ == SourceType.DISTRIBUTION_PACKAGE:
            return object.__new__(DistributionPackageSource)

        return super().__new__(cls)

    @classmethod
    def from_import_path(cls: Type[S], import_path: str) -> S:
        if not import_path:
            raise ValueError("Invalid import path.")

        # Remove internal version pins for backwards compatability
        if "@" in import_path:
            import_path = import_path.split("@", 1)[0]

        if "." in import_path:
            module, attribute = import_path.rsplit(".", maxsplit=1)
        else:
            module = import_path
            attribute = None

        return cls(module=module, attribute=attribute, type=SourceType.UNKNOWN)

    @property
    def import_path(self) -> str:
        if self.attribute:
            return f"{self.module}.{self.attribute}"
        else:
            return self.module

    @property
    def is_internal(self) -> bool:
        if self.type not in {
            SourceType.UNKNOWN,
            SourceType.DISTRIBUTION_PACKAGE,
        }:
            return False

        # Covers both the root `zenml` module and any submodules
        return self.import_path == "zenml" or self.import_path.startswith(
            "zenml."
        )

    @property
    def is_module_source(self) -> bool:
        return self.attribute is None


class DistributionPackageSource(Source):
    version: Optional[str] = None
    type: SourceType = SourceType.DISTRIBUTION_PACKAGE

    @validator("type")
    def _validate_type(cls, value: SourceType) -> SourceType:
        if value != SourceType.DISTRIBUTION_PACKAGE:
            raise ValueError("Invalid source type.")

        return value

    @property
    def package_name(self) -> Optional[str]:
        from zenml.utils import source_utils_v2

        return source_utils_v2._get_package_for_module(module_name=self.module)


class CodeRepositorySource(Source):
    repository_id: UUID
    commit: str
    subdirectory: str
    type: SourceType = SourceType.CODE_REPOSITORY

    @validator("type")
    def _validate_type(cls, value: SourceType) -> SourceType:
        if value != SourceType.CODE_REPOSITORY:
            raise ValueError("Invalid source type.")

        return value
