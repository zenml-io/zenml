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
from zenml.new_models.base.base import (
    BaseZenModel,
    BaseRequest,
    BaseResponseBody,
    BaseResponseMetadata,
    BaseResponse,
)
from zenml.new_models.base.scoped import (
    UserScopedRequest,
    UserScopedResponseBody,
    UserScopedResponseMetadata,
    UserScopedResponse,
    WorkspaceScopedRequest,
    WorkspaceScopedResponseBody,
    WorkspaceScopedResponseMetadata,
    WorkspaceScopedResponse,
    ShareableRequest,
    SharableResponseBody,
    SharableResponseMetadata,
    ShareableResponse,
)
from zenml.new_models.base.filter import (
    BaseFilter,
    UserScopedFilter,
    WorkspaceScopedFilter,
    ShareableFilter,
    NumericFilter,
    StrFilter,
    BoolFilter,
    UUIDFilter,
)
from zenml.new_models.base.utils import update_model, hydrated_property
from zenml.new_models.base.page import Page
