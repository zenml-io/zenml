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

from typing import TYPE_CHECKING, Any, Optional, Set, Type

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    PlainValidator,
    WrapValidator,
)

from zenml.logger import get_logger
from zenml.utils import secret_utils

logger = get_logger(__name__)


def check_validators(
    pydantic_class: Type[BaseModel],
    field_name: Optional[str] = None,
) -> bool:
    """Function to check if a Pydantic model or a pydantic field has validators.

    Args:
        pydantic_class: The class defining the pydantic model.
        field_name: Optional, field info. If specified, this function will focus
            on a singular field within the class. If not specified, it will
            check model validators.

    Returns:
        boolean, indicating whether the specified field or class has a validator
    """
    # If field is not specified check model validators
    if field_name is None:
        if pydantic_class.__pydantic_decorators__.model_validators:
            return True

    # Else, check field validators
    else:
        # 1. Field validators can be defined through @field_validator decorators
        f_validators = pydantic_class.__pydantic_decorators__.field_validators

        for name, f_v in f_validators.items():
            if field_name in f_v.info.fields:
                return True

        # 2. Field validators can be defined through the Annotation[.....]
        field_info = pydantic_class.model_fields[field_name]
        if metadata := field_info.metadata:
            if any(
                isinstance(
                    m,
                    (
                        AfterValidator,
                        BeforeValidator,
                        PlainValidator,
                        WrapValidator,
                    ),
                )
                for m in metadata
            ):
                return True

    return False


class SecretReferenceMixin(BaseModel):
    """Mixin class for secret references in pydantic model attributes."""

    def __init__(
        self, warn_about_plain_text_secrets: bool = False, **kwargs: Any
    ) -> None:
        """Ensures that secret references are only passed for valid fields.

        This method ensures that secret references are not passed for fields
        that explicitly prevent them or require pydantic validation.

        Args:
            warn_about_plain_text_secrets: If true, then warns about using plain-text secrets.
            **kwargs: Arguments to initialize this object.

        Raises:
            ValueError: If an attribute that requires custom pydantic validation
                or an attribute which explicitly disallows secret references
                is passed as a secret reference.
        """
        for key, value in kwargs.items():
            try:
                field = self.__class__.model_fields[key]
            except KeyError:
                # Value for a private attribute or non-existing field, this
                # will fail during the upcoming pydantic validation
                continue

            if value is None:
                continue

            if not secret_utils.is_secret_reference(value):
                if (
                    secret_utils.is_secret_field(field)
                    and warn_about_plain_text_secrets
                ):
                    logger.warning(
                        "You specified a plain-text value for the sensitive "
                        f"attribute `{key}`. This is currently only a warning, "
                        "but future versions of ZenML will require you to pass "
                        "in sensitive information as secrets. Check out the "
                        "documentation on how to configure values with secrets "
                        "here: https://docs.zenml.io/user-guide/advanced-guide/secret-management"
                    )
                continue

            if secret_utils.is_clear_text_field(field):
                raise ValueError(
                    f"Passing the `{key}` attribute as a secret reference is "
                    "not allowed."
                )

            requires_validation = check_validators(
                pydantic_class=self.__class__, field_name=key
            )
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
            KeyError: If the secret or secret key don't exist.

        Returns:
            The (potentially resolved) attribute value.
        """
        value = super().__getattribute__(key)

        if not secret_utils.is_secret_reference(value):
            return value

        from zenml.client import Client

        secret_ref = secret_utils.parse_secret_reference(value)

        # Try to resolve the secret using the secret store
        try:
            secret = Client().get_secret_by_name_and_scope(
                name=secret_ref.name,
            )
        except (KeyError, NotImplementedError):
            raise KeyError(
                f"Failed to resolve secret reference for attribute {key}: "
                f"The secret {secret_ref.name} does not exist."
            )

        if secret_ref.key not in secret.values:
            raise KeyError(
                f"Failed to resolve secret reference for attribute {key}: "
                f"The secret {secret_ref.name} does not contain a value "
                f"for key {secret_ref.key}. Available keys: "
                f"{set(secret.values.keys())}."
            )

        return secret.secret_values[secret_ref.key]

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
