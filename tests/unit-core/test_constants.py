#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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

import os

from zenml.constants import handle_int_env_var


def test_handle_int_env_var():
    """Check handle_int_env_var in all cases"""
    env_var = "ZENML_TEST_HANDLE_INT_ENV_VAR"

    # check value error (when it can't be converted to int)
    os.environ[env_var] = "test"
    assert 0 == handle_int_env_var(env_var, 0)

    # check if it isn't there (in case it doesn't exist)
    del os.environ[env_var]
    assert 0 == handle_int_env_var(env_var, 0)
