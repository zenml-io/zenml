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
"""Source classes."""
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Extra, validator

from zenml.logger import get_logger

logger = get_logger(__name__)


class SourceType(Enum):
    """Enum representing different types of sources."""

    USER = "user"
    BUILTIN = "builtin"
    INTERNAL = "internal"
    DISTRIBUTION_PACKAGE = "distribution_package"
    CODE_REPOSITORY = "code_repository"
    UNKNOWN = "unknown"


class Source(BaseModel):
    """Source specification.

    Attributes:
        module: The module name.
        attribute: Optional name of the attribute inside the module.
        type: The type of the source.
    """

    module: str
    attribute: Optional[str] = None
    type: SourceType

    # TODO: Adding this code messes with FastAPI as they do some kind of
    # validation the prevents subclasses for response model fields
    # def __new__(cls, **kwargs: Any) -> "Source":
    #     type_ = kwargs.get("type")
    #     type_ = SourceType(type_) if type_ else None

    #     if type_ == SourceType.CODE_REPOSITORY:
    #         return object.__new__(CodeRepositorySource)
    #     elif type_ == SourceType.DISTRIBUTION_PACKAGE:
    #         return object.__new__(DistributionPackageSource)

    #     return super().__new__(cls)

    @classmethod
    def from_import_path(cls, import_path: str) -> "Source":
        """Creates a source from an import path.

        Args:
            import_path: The import path.

        Raises:
            ValueError: If the import path is empty.

        Returns:
            The source.
        """
        if not import_path:
            raise ValueError(
                "Invalid empty import path. The import path needs to refer "
                "to a Python module and an optional attribute of that module."
            )

        # Remove internal version pins for backwards compatability
        if "@" in import_path:
            import_path = import_path.split("@", 1)[0]

        if "." in import_path:
            module, attribute = import_path.rsplit(".", maxsplit=1)
        else:
            module = import_path
            attribute = None

        return Source(
            module=module, attribute=attribute, type=SourceType.UNKNOWN
        )

    @property
    def import_path(self) -> str:
        """The import path of the source.

        Returns:
            The import path of the source.
        """
        if self.attribute:
            return f"{self.module}.{self.attribute}"
        else:
            return self.module

    @property
    def is_internal(self) -> bool:
        """If the source is internal (=from the zenml package).

        Returns:
            True if the source is internal, False otherwise
        """
        if self.type not in {
            SourceType.UNKNOWN,
            SourceType.DISTRIBUTION_PACKAGE,
        }:
            return False

        return self.import_path.split(".", maxsplit=1)[0] == "zenml"

    @property
    def is_module_source(self) -> bool:
        """If the source is a module source.

        Returns:
            If the source is a module source.
        """
        return self.attribute is None

    class Config:
        """Pydantic config class."""

        extra = Extra.allow


class DistributionPackageSource(Source):
    """Source representing an object from a distribution package.

    Attributes:
        version: The package version.
    """

    version: Optional[str] = None
    type: SourceType = SourceType.DISTRIBUTION_PACKAGE

    @validator("type")
    def _validate_type(cls, value: SourceType) -> SourceType:
        """Validate the source type.

        Args:
            value: The source type.

        Raises:
            ValueError: If the source type is not `DISTRIBUTION_PACKAGE`.

        Returns:
            The source type.
        """
        if value != SourceType.DISTRIBUTION_PACKAGE:
            raise ValueError("Invalid source type.")

        return value

    @property
    def package_name(self) -> Optional[str]:
        """The package name.

        Returns:
            The package name if a package for the source module exists.
        """
        from zenml.utils import source_utils_v2

        return source_utils_v2._get_package_for_module(module_name=self.module)


class CodeRepositorySource(Source):
    """Source representing an object from a code repository.

    Attributes:
        repository_id: The code repository ID.
        commit: The commit.
        subdirectory: The subdirectory of the source root inside the code
            repository.
    """

    repository_id: UUID
    commit: str
    subdirectory: str
    type: SourceType = SourceType.CODE_REPOSITORY

    @validator("type")
    def _validate_type(cls, value: SourceType) -> SourceType:
        """Validate the source type.

        Args:
            value: The source type.

        Raises:
            ValueError: If the source type is not `CODE_REPOSITORY`.

        Returns:
            The source type.
        """
        if value != SourceType.CODE_REPOSITORY:
            raise ValueError("Invalid source type.")

        return value
