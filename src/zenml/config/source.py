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
from typing import TYPE_CHECKING, Any, Dict, Optional
from uuid import UUID

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    SerializeAsAny,
    field_validator,
)
from typing_extensions import Annotated

from zenml.logger import get_logger

if TYPE_CHECKING:
    AnyClassMethod = classmethod[Any]  # type: ignore[type-arg]

logger = get_logger(__name__)


class SourceType(Enum):
    """Enum representing different types of sources."""

    USER = "user"
    BUILTIN = "builtin"
    INTERNAL = "internal"
    DISTRIBUTION_PACKAGE = "distribution_package"
    CODE_REPOSITORY = "code_repository"
    NOTEBOOK = "notebook"
    UNKNOWN = "unknown"


class Source(BaseModel):
    """Source specification.

    A source specifies a module name as well as an optional attribute of that
    module. These values can be used to import the module and get the value
    of the attribute inside the module.

    Example:
        The source `Source(module="zenml.config.source", attribute="Source")`
        references the class that this docstring is describing. This class is
        defined in the `zenml.config.source` module and the name of the
        attribute is the class name `Source`.

    Attributes:
        module: The module name.
        attribute: Optional name of the attribute inside the module.
        type: The type of the source.
    """

    module: str
    attribute: Optional[str] = None
    type: SourceType

    @classmethod
    def from_import_path(
        cls, import_path: str, is_module_path: bool = False
    ) -> "Source":
        """Creates a source from an import path.

        Args:
            import_path: The import path.
            is_module_path: If the import path points to a module or not.

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

        # Remove internal version pins for backwards compatibility
        if "@" in import_path:
            import_path = import_path.split("@", 1)[0]

        if is_module_path or "." not in import_path:
            module = import_path
            attribute = None
        else:
            module, attribute = import_path.rsplit(".", maxsplit=1)

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
        if self.type not in {SourceType.UNKNOWN, SourceType.INTERNAL}:
            return False

        return self.module.split(".", maxsplit=1)[0] == "zenml"

    @property
    def is_module_source(self) -> bool:
        """If the source is a module source.

        Returns:
            If the source is a module source.
        """
        return self.attribute is None

    model_config = ConfigDict(extra="allow")

    def model_dump(self, **kwargs: Any) -> Dict[str, Any]:
        """Dump the source as a dictionary.

        Args:
            **kwargs: Additional keyword arguments.

        Returns:
            The source as a dictionary.
        """
        return super().model_dump(serialize_as_any=True, **kwargs)

    def model_dump_json(self, **kwargs: Any) -> str:
        """Dump the source as a JSON string.

        Args:
            **kwargs: Additional keyword arguments.

        Returns:
            The source as a JSON string.
        """
        return super().model_dump_json(serialize_as_any=True, **kwargs)


class DistributionPackageSource(Source):
    """Source representing an object from a distribution package.

    Attributes:
        package_name: Name of the package.
        version: The package version.
    """

    package_name: str
    version: Optional[str] = None
    type: SourceType = SourceType.DISTRIBUTION_PACKAGE

    @field_validator("type")
    @classmethod
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

    @field_validator("type")
    @classmethod
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


class NotebookSource(Source):
    """Source representing an object defined in a notebook.

    Attributes:
        cell_id: ID of the notebook cell in which the object is stored. This
            will only be set for objects which explicitly store this by calling
            `zenml.utils.notebook_utils.save_notebook_cell_id()`.
        replacement_module: Replacement module from which to load the source
            when not running in a notebook. This will only be set for special
            object for which we extract the cell code in which they're defined
            into python files before running pipeline remotely.
    """

    cell_id: Optional[str] = None
    replacement_module: Optional[str] = None
    type: SourceType = SourceType.NOTEBOOK

    @field_validator("type")
    @classmethod
    def _validate_type(cls, value: SourceType) -> SourceType:
        """Validate the source type.

        Args:
            value: The source type.

        Raises:
            ValueError: If the source type is not `NOTEBOOK`.

        Returns:
            The source type.
        """
        if value != SourceType.NOTEBOOK:
            raise ValueError("Invalid source type.")

        return value

    @field_validator("module")
    @classmethod
    def _validate_module(cls, value: str) -> str:
        """Validate the module.

        Args:
            value: The module.

        Raises:
            ValueError: If the module is not `__main__`.

        Returns:
            The module.
        """
        if value != "__main__":
            raise ValueError("Invalid module for notebook source.")

        return value


def convert_source(source: Any) -> Any:
    """Converts an old source string to a source object.

    Args:
        source: Source string or object.

    Returns:
        The converted source.
    """
    if isinstance(source, str):
        source = Source.from_import_path(source)

    return source


SourceWithValidator = Annotated[
    SerializeAsAny[Source],
    BeforeValidator(convert_source),
]
