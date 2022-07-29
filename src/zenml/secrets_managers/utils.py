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
"""Utility functions for the ZenML secrets manager module."""

import base64
from typing import Any, Dict, Tuple

from zenml.constants import ZENML_SCHEMA_NAME
from zenml.secret.base_secret import BaseSecretSchema


def encode_string(string: str) -> str:
    """Base64 encode a string.

    Args:
        string: String to encode

    Returns:
        Encoded string
    """
    encoded_bytes = base64.b64encode(string.encode("utf-8"))
    return str(encoded_bytes, "utf-8")


def encode_secret(secret: BaseSecretSchema) -> Dict[str, str]:
    """Base64 encode all values within a secret.

    Args:
        secret: Secret containing key-value pairs

    Returns:
        Encoded secret Dict containing key-value pairs
    """
    encoded_secret = {
        k: encode_string(str(v))
        for k, v in secret.content.items()
        if v is not None
    }
    encoded_secret[ZENML_SCHEMA_NAME] = secret.TYPE
    return encoded_secret


def decode_string(string: str) -> str:
    """Base64 decode a string.

    Args:
        string: String to decode

    Returns:
        Decoded string
    """
    decoded_bytes = base64.b64decode(string)
    return str(decoded_bytes, "utf-8")


def decode_secret_dict(
    secret_dict: Dict[str, str]
) -> Tuple[Dict[str, str], str]:
    """Base64 decode a Secret.

    Args:
        secret_dict: dict containing key-value pairs to decode

    Returns:
        Decoded secret Dict containing key-value pairs
    """
    zenml_schema_name = secret_dict.pop(ZENML_SCHEMA_NAME)

    decoded_secret = {k: decode_string(v) for k, v in secret_dict.items()}
    return decoded_secret, zenml_schema_name


def secret_to_dict(
    secret: BaseSecretSchema, encode: bool = False
) -> Dict[str, Any]:
    """Converts a secret to a dict representation with the schema.

    This includes the schema type in the secret's JSON representation, so that
    the correct SecretSchema can be retrieved when the secret is loaded.

    Args:
        secret: a subclass of the BaseSecretSchema class
        encode: if true, encodes the secret values using base64 encoding

    Returns:
        A dict representation containing all key-value pairs and the ZenML
        schema type.
    """
    if encode:
        secret_contents = encode_secret(secret)
    else:
        secret_contents = secret.content
        secret_contents[ZENML_SCHEMA_NAME] = secret.TYPE

    return secret_contents


def secret_from_dict(
    secret_dict: Dict[str, Any], secret_name: str = "", decode: bool = False
) -> BaseSecretSchema:
    """Converts a dictionary secret representation into a secret.

    Args:
        secret_dict: a dictionary representation of a secret
        secret_name: optional name for the secret, defaults to empty string
        decode: if true, decodes the secret values using base64

    Returns:
        A secret instance containing all key-value pairs loaded from the JSON
        representation and of the ZenML schema type indicated in the JSON.
    """
    from zenml.secret.secret_schema_class_registry import (
        SecretSchemaClassRegistry,
    )

    secret_contents = secret_dict.copy()

    if decode:
        secret_contents, zenml_schema_name = decode_secret_dict(secret_contents)
    else:
        zenml_schema_name = secret_contents.pop(ZENML_SCHEMA_NAME)

    secret_contents["name"] = secret_name

    secret_schema = SecretSchemaClassRegistry.get_class(
        secret_schema=zenml_schema_name
    )
    return secret_schema(**secret_contents)
