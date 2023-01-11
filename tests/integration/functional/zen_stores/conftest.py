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
import tempfile
from pathlib import Path
from typing import Dict, Union

import pytest

from tests.integration.functional.conftest import (
    constant_int_output_test_step,
    int_plus_one_test_step,
)
from zenml.client import Client
from zenml.config.global_config import GlobalConfiguration
from zenml.enums import PermissionType
from zenml.models import (
    ProjectRequestModel,
    RoleRequestModel,
    TeamRequestModel,
    UserRequestModel,
)
from zenml.models.base_models import BaseResponseModel
from zenml.zen_stores.base_zen_store import BaseZenStore
from zenml.zen_stores.sql_zen_store import SqlZenStoreConfiguration


# @pytest.fixture
# def sql_store(
#     module_clean_client: Client,
# ) -> Dict[str, Union[BaseZenStore, BaseResponseModel]]:
#
#     original_config = GlobalConfiguration.get_instance()
#     original_client = Client.get_instance()
#
#     GlobalConfiguration._reset_instance()
#     Client._reset_instance()
#
#     temp_dir = tempfile.TemporaryDirectory(suffix="_zenml_sql_test")
#     gc = GlobalConfiguration()
#     gc.analytics_opt_in = False
#     gc.set_store(
#         config=SqlZenStoreConfiguration(
#             url=f"sqlite:///{Path(temp_dir.name) / 'store.db'}"
#         ),
#         track_analytics=False,
#     )
#     client = Client()
#     _ = client.zen_store
#
#     store = gc.zen_store
#     default_project = store._default_project
#     active_user = store.get_user()
#     default_stack = store._get_default_stack(
#         project_name_or_id=default_project.id, user_name_or_id=active_user.id
#     )
#     yield {
#         "store": store,
#         "default_project": default_project,
#         "default_stack": default_stack,
#         "active_user": active_user,
#     }
#
#     # restore the global configuration and the client
#     GlobalConfiguration._reset_instance(original_config)
#     Client._reset_instance(original_client)
#
#
# @pytest.fixture
# def sql_store_with_run(
#     sql_store,
#     connected_two_step_pipeline,
# ) -> Dict[str, Union[BaseZenStore, BaseResponseModel]]:
#
#     pipeline_instance = connected_two_step_pipeline(
#         step_1=constant_int_output_test_step(),
#         step_2=int_plus_one_test_step(),
#     )
#     pipeline_instance.run(unlisted=True)
#
#     store = sql_store["store"]
#     pipeline_run = store.list_runs()[0]
#     pipeline_step = store.list_run_steps()[1]
#     artifact = store.list_artifacts()[0]
#     sql_store.update(
#         {
#             "pipeline_run": pipeline_run,
#             "step": pipeline_step,
#             "artifact": artifact,
#         }
#     )
#
#     yield sql_store
#
#
# @pytest.fixture
# def sql_store_with_runs(
#     sql_store,
#     connected_two_step_pipeline,
# ) -> Dict[str, Union[BaseZenStore, BaseResponseModel]]:
#
#     for _ in range(10):
#         pipeline_instance = connected_two_step_pipeline(
#             step_1=constant_int_output_test_step(),
#             step_2=int_plus_one_test_step(),
#         )
#         pipeline_instance.run(unlisted=True)
#
#     store = sql_store["store"]
#     pipeline_runs = store.list_runs()
#
#     sql_store.update(
#         {
#             "pipeline_runs": pipeline_runs,
#         }
#     )
#
#     yield sql_store
#
#
# @pytest.fixture
# def sql_store_with_team(
#     sql_store,
# ) -> Dict[str, Union[BaseZenStore, BaseResponseModel]]:
#
#     store = sql_store["store"]
#
#     new_team = TeamRequestModel(name="arias_team")
#     default_team = store.create_team(new_team)
#
#     sql_store.update(
#         {
#             "default_team": default_team,
#         }
#     )
#
#     yield sql_store
#
#
# @pytest.fixture
# def sql_store_with_user_team_role(
#     sql_store,
# ) -> Dict[str, Union[BaseZenStore, BaseResponseModel]]:
#     store = sql_store["store"]
#
#     new_team = TeamRequestModel(name="axls_team")
#     new_team = store.create_team(new_team)
#
#     new_role = RoleRequestModel(
#         name="axl_feeder", permissions={PermissionType.ME}
#     )
#     new_role = store.create_role(new_role)
#
#     new_user = UserRequestModel(name="axl")
#     new_user = store.create_user(new_user)
#
#     new_project = ProjectRequestModel(name="axl_prj")
#     new_project = store.create_project(new_project)
#
#     yield {
#         "store": store,
#         "user": new_user,
#         "team": new_team,
#         "role": new_role,
#         "project": new_project,
#     }
