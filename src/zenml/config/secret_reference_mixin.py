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
"""Secret reference mixin implementation."""
from typing import TYPE_CHECKING, Any, Set

from pydantic import BaseModel

from zenml.logger import get_logger
from zenml.utils import secret_utils

logger = get_logger(__name__)


class SecretReferenceMixin(BaseModel):
    """Mixin class for secret references in pydantic model attributes."""

    def __init__(self, **kwargs: Any) -> None:
        """Ensures that secret references are only passed for valid fields.

        This method ensures that secret references are not passed for fields
        that explicitly prevent them or require pydantic validation.

        Args:
            **kwargs: Arguments to initialize this object.

        Raises:
            ValueError: If an attribute that requires custom pydantic validation
                or an attribute which explicitly disallows secret references is
                is passed as a secret reference.
        """
        for key, value in kwargs.items():
            try:
                field = self.__class__.__fields__[key]
            except KeyError:
                # Value for a private attribute or non-existing field, this
                # will fail during the upcoming pydantic validation
                continue

            if value is None:
                continue

            if not secret_utils.is_secret_reference(value):
                if secret_utils.is_secret_field(field):
                    logger.warning(
                        "You specified a plain-text value for the sensitive "
                        f"attribute `{key}`. This is currently only a warning, "
                        "but future versions of ZenML will require you to pass "
                        "in sensitive information as secrets. Check out the "
                        "documentation on how to configure values with secrets "
                        "here: https://docs.zenml.io/advanced-guide/practical/secrets-management"
                    )
                continue

            if secret_utils.is_clear_text_field(field):
                raise ValueError(
                    f"Passing the `{key}` attribute as a secret reference is "
                    "not allowed."
                )

            requires_validation = field.pre_validators or field.post_validators
            if requires_validation:
                raise ValueError(
                    f"Passing the attribute `{key}` as a secret reference is "
                    "not allowed as additional validation is required for "
                    "this attribute."
                )

        super().__init__(**kwargs)

    def __custom_getattribute__(self, key: str) -> Any:
        """Returns the (potentially resolved) attribute value for the given key.

        An attribute value may be either specified directly, or as a secret
        reference. In case of a secret reference, this method resolves the
        reference and returns the secret value instead.

        Args:
            key: The key for which to get the attribute value.

        Raises:
            RuntimeError: If the active stack is missing a secrets manager.
            KeyError: If the secret or secret key don't exist.

        Returns:
            The (potentially resolved) attribute value.
        """
        value = super().__getattribute__(key)

        if not secret_utils.is_secret_reference(value):
            return value

        from zenml.client import Client

        secrets_manager = Client().active_stack.secrets_manager
        if not secrets_manager:
            raise RuntimeError(
                f"Failed to resolve secret reference for attribute {key}: "
                "The active stack does not have a secrets manager."
            )

        secret_ref = secret_utils.parse_secret_reference(value)
        try:
            secret = secrets_manager.get_secret(secret_ref.name)
        except KeyError:
            raise KeyError(
                f"Failed to resolve secret reference for attribute {key}: "
                f"The secret {secret_ref.name} does not exist."
            )

        try:
            secret_value = secret.content[secret_ref.key]
        except KeyError:
            raise KeyError(
                f"Failed to resolve secret reference for attribute {key}: "
                f"The secret {secret_ref.name} does not contain a value for key "
                f"{secret_ref.key}. Available keys: {set(secret.content)}."
            )

        return str(secret_value)

    if not TYPE_CHECKING:
        # When defining __getattribute__, mypy allows accessing non-existent
        # attributes without failing
        # (see https://github.com/python/mypy/issues/13319).
        __getattribute__ = __custom_getattribute__

    @property
    def required_secrets(self) -> Set[secret_utils.SecretReference]:
        """All required secrets for this object.

        Returns:
            The required secrets of this object.
        """
        return {
            secret_utils.parse_secret_reference(v)
            for v in self.dict().values()
            if secret_utils.is_secret_reference(v)
        }
