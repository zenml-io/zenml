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
"""Constants used by ZenML domain models."""

# The maximum length of a name string fields in models.
MODEL_NAME_FIELD_MAX_LENGTH = 255
# The maximum length of description string fields in models.
MODEL_DESCRIPTIVE_FIELD_MAX_LENGTH = 300
# The maximum length of a URI string field in models.
MODEL_URI_FIELD_MAX_LENGTH = 1000
# The maximum length of a metadata field in models.
MODEL_METADATA_FIELD_MAX_LENGTH = 200
# The maximum length of a docstring field in models.
MODEL_DOCSTRING_FIELD_MAX_LENGTH = 15000
# The maximum length of a TEXT field in models.
MODEL_TEXT_FIELD_MAX_LENGTH = 650000

TEXT_FIELD_MAX_LENGTH = 65535
STR_FIELD_MAX_LENGTH = 255

# The maximum length of a password
# NOTE: this should be kept under 50 characters to avoid problems with
# the hashing algorithm
# (https://security.stackexchange.com/questions/39849/does-bcrypt-have-a-maximum-password-length).
USER_PASSWORD_MAX_LENGTH = 50

USER_ACTIVATION_TOKEN_LENGTH = 64
