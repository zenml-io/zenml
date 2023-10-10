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
from zenml.new_models.base.base_models import (
    BaseResponseModel,
    BaseResponseModelMetadata,
    BaseRequestModel,
)
from zenml.new_models.base.scoped_models import (
    UserScopedRequestModel,
    UserScopedResponseModel,
    UserScopedResponseMetadataModel,
    WorkspaceScopedRequestModel,
    WorkspaceScopedResponseModel,
    WorkspaceScopedResponseMetadataModel,
    ShareableRequestModel,
    ShareableResponseModel,
    SharableResponseMetadataModel,
)
from zenml.new_models.base.utils import update_model, hydrated_property
