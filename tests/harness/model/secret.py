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
"""ZenML test secrets models."""

import logging
import os
from typing import TYPE_CHECKING, Any, Dict, Optional

from pydantic import Field

from tests.harness.model.base import BaseTestConfigModel
from zenml.utils.secret_utils import PlainSerializedSecretStr

if TYPE_CHECKING:
    from tests.harness.harness import TestHarness


class Secret(BaseTestConfigModel):
    """Configuration secret."""

    name: str = Field(pattern="^[A-Z][A-Z0-9_]+$")
    value: PlainSerializedSecretStr


class BaseTestSecretConfigModel(BaseTestConfigModel):
    """Base class for models that can reference secrets in their field values."""

    def _get_secret_name(self, value: Any) -> Optional[str]:
        """Get the name of the secret that the value references.

        A secret can be referenced in a field value using the
        {{ secret_name }} syntax.

        Args:
            value: The value to check.

        Returns:
            The name of the referenced secret, or None if the value does not
            reference a secret.
        """
        if (
            isinstance(value, str)
            and value.startswith("{{")
            and value.endswith("}}")
        ):
            return value[2:-2]

        return None

    def _resolve_secret(self, secret_name: str, value: str) -> str:
        """Resolves a secret.

        Args:
            secret_name: The secret name.
            value: The original value.

        Returns:
            The resolved secret value.
        """
        from tests.harness.harness import TestHarness

        if secret_name.upper() in os.environ:
            return os.environ[secret_name.upper()]

        secret = TestHarness().get_secret(secret_name)

        if secret:
            return secret.value.get_secret_value()

        logging.error(f"Secret '{secret_name}' could not be resolved.")
        return value

    def __custom_getattribute__(self, key: str) -> Any:
        """Custom __getattribute__ implementation that resolves secrets.

        If a value for this attribute was specified using the {{ secret_name }}
        syntax, the resolved secret value is returned instead of the original
        value.

        Args:
            key: The attribute name.

        Returns:
            The attribute value.
        """
        value = super().__getattribute__(key)
        if key.startswith("_") or key not in type(self).model_fields:
            return value

        secret_name = self._get_secret_name(value)
        if secret_name:
            return self._resolve_secret(secret_name, value)

        return value

    if not TYPE_CHECKING:
        # When defining __getattribute__, mypy allows accessing non-existent
        # attributes without failing
        # (see https://github.com/python/mypy/issues/13319).
        __getattribute__ = __custom_getattribute__

    def compile(self, harness: "TestHarness") -> None:
        """Validates and compiles the configuration when part of a test harness.

        Checks that all referenced secrets are defined in the test harness

        Args:
            harness: The test harness to validate against.
        """
        for field in type(self).model_fields.keys():
            secret_name = self._get_secret_name(getattr(self, field))
            if secret_name:
                # Check that the secret is defined in the test harness
                # configuration. Calling this will raise an exception if the
                # secret is not defined in the test harness configuration
                # or using environment variables.
                try:
                    self._resolve_secret(secret_name, "")
                except ValueError:
                    logging.warning(
                        f"Secret '{secret_name}' is referenced in field "
                        f"'{field}' of model '{type(self).__name__}' but is "
                        f"not defined in the test configuration or "
                        f"using environment variables."
                    )

    def dict(self, **kwargs: Any) -> Dict[str, Any]:
        """Resolve secrets in the dictionary representation.

        Args:
            **kwargs: Additional keyword arguments to include in the dictionary.

        Returns:
            The dictionary representation of the model.
        """
        d = super().model_dump(**kwargs)
        for key, value in d.items():
            secret_name = self._get_secret_name(value)
            if secret_name:
                d[key] = self._resolve_secret(secret_name, value)

        return d
