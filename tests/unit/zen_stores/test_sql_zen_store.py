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


from uuid import UUID

from zenml.models.user_management_models import ProjectModel
from zenml.zen_stores.base_zen_store import BaseZenStore

#  .---------.
# | PROJECTS |
# '----------'


def test_only_one_default_project(fresh_sql_zen_store: BaseZenStore):
    """Tests that only one default project can be created."""
    assert fresh_sql_zen_store.projects == fresh_sql_zen_store.list_projects()
    assert len(fresh_sql_zen_store.projects) == 1
    assert len(fresh_sql_zen_store.list_projects()) == 1


def test_project_creation(fresh_sql_zen_store: BaseZenStore):
    """Tests project creation."""
    new_project = ProjectModel(name="test_project")
    fresh_sql_zen_store.create_project(new_project)
    projects_list = fresh_sql_zen_store.list_projects()
    assert len(projects_list) == 2
    assert projects_list[1].name == "test_project"


def test_getting_project(fresh_sql_zen_store: BaseZenStore):
    """Tests getting a project."""
    default_project = fresh_sql_zen_store.get_project("default")
    assert default_project.name == "default"
    assert type(default_project.id) == UUID


def test_updating_project(fresh_sql_zen_store: BaseZenStore):
    """Tests updating a project."""
    default_project = fresh_sql_zen_store.get_project("default")
    assert default_project.name == "default"
    default_project.name = "new_name"
    fresh_sql_zen_store.update_project("default", default_project)
    assert fresh_sql_zen_store.list_projects()[0].name == "new_name"


def test_deleting_project(fresh_sql_zen_store: BaseZenStore):
    """Tests deleting a project."""
    fresh_sql_zen_store.delete_project("default")
    assert len(fresh_sql_zen_store.list_projects()) == 0
