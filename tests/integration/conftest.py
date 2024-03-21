#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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


import pytest

from zenml.client import Client
from zenml.models import TagFilter


@pytest.fixture(scope="function", autouse=True)
def cleanup_after_test():
    def clean_objects(
        list_fn,
        del_fn,
        del_fields=None,
        pre_objects=None,
        extra_args=None,
        list_args=None,
    ):
        if pre_objects is None:
            pre_objects = set()
        if del_fields is None:
            del_fields = []
        if list_args is None:
            list_args = {"size": 1000}
        while objects := list_fn(**list_args).items:
            something_deleted = False
            for o in objects:
                if o.id not in pre_objects:
                    del_fn(
                        str(o.id),
                        *(
                            [getattr(o, df) for df in del_fields]
                            + (extra_args if extra_args else [])
                        ),
                    )
                    something_deleted = True
            if not something_deleted:
                break

    # keeping track of objects which might be created to make tests runnable
    client = Client()
    pre_workspaces = {i.id for i in client.list_workspaces(size=1000).items}
    pre_users = {i.id for i in client.list_users(size=1000).items}
    pre_stacks = {i.id for i in client.list_stacks(size=1000).items}
    pre_stack_components = {
        i.id for i in client.list_stack_components(size=1000).items
    }
    try:
        yield
    finally:
        client = Client()
        clean_objects(
            client.list_workspaces,
            client.delete_workspace,
            pre_objects=pre_workspaces,
        )
        clean_objects(
            client.list_users, client.delete_user, pre_objects=pre_users
        )

        while pipelines := client.list_pipelines().items:
            for p in pipelines:
                try:
                    while pipeline := client.get_pipeline(
                        name_id_or_prefix=p.id, version=None
                    ):
                        client.zen_store.delete_pipeline(
                            pipeline_id=pipeline.id
                        )
                except KeyError:
                    pass
        clean_objects(client.list_builds, client.delete_build)
        clean_objects(
            client.list_code_repositories, client.delete_code_repository
        )
        clean_objects(client.list_deployments, client.delete_deployment)
        clean_objects(client.list_schedules, client.delete_schedule)
        clean_objects(client.list_models, client.delete_model)
        clean_objects(client.list_artifacts, client.delete_artifact)
        clean_objects(
            client.list_tags,
            client.delete_tag,
            list_args={"tag_filter_model": TagFilter(size=1000)},
        )

        client.activate_stack("default")
        clean_objects(
            client.list_stacks,
            client.delete_stack,
            pre_objects=pre_stacks,
            extra_args=[True],
        )
        clean_objects(
            client.list_stack_components,
            client.delete_stack_component,
            del_fields=["type"],
            pre_objects=pre_stack_components,
        )
