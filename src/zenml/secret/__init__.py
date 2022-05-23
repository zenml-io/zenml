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
"""
A ZenML Secret is a grouping of key-value pairs. These are accessed and
administered via the ZenML Secret Manager (a stack component).

Secrets are distinguished by having different schemas. An AWS SecretSchema, for
example, has key-value pairs for `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
as well as an optional `AWS_SESSION_TOKEN`. If you don't specify a schema at the
point of registration, ZenML will set the schema as `ArbitrarySecretSchema`, a
kind of default schema where things that aren't attached to a grouping can be
stored.
"""
from zenml.secret.arbitrary_secret_schema import (
    ARBITRARY_SECRET_SCHEMA_TYPE,
    ArbitrarySecretSchema,
)
from zenml.secret.base_secret import BaseSecretSchema
from zenml.secret.secret_schema_class_registry import (
    SecretSchemaClassRegistry,
    register_secret_schema_class,
)

__all__ = [
    "ARBITRARY_SECRET_SCHEMA_TYPE",
    "ArbitrarySecretSchema",
    "BaseSecretSchema",
    "SecretSchemaClassRegistry",
    "register_secret_schema_class",
]
