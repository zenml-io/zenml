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
from zenml.enums import StackComponentType
from zenml.models import TagFilter


@pytest.fixture(scope="function", autouse=True)
def cleanup_after_test():
    try:
        yield
    finally:
        client = Client()
        while workspaces := client.list_workspaces().items:
            if len(workspaces) <= 1:
                break
            for ws in workspaces:
                if ws.name != "default":
                    client.delete_workspace(ws.id)
        while users := client.list_users().items:
            if len(users) <= 1:
                break
            for u in users:
                if u.name != "default":
                    client.delete_user(u.id)
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
        while pipeline_builds := client.list_builds().items:
            for pb in pipeline_builds:
                client.delete_build(str(pb.id))
        while code_repositories := client.list_code_repositories().items:
            for cr in code_repositories:
                client.delete_code_repository(cr.id)
        while deployments := client.list_deployments().items:
            for d in deployments:
                client.delete_deployment(str(d.id))
        while schedules := client.list_schedules().items:
            for s in schedules:
                client.delete_schedule(s.id)
        while models := client.list_models().items:
            for m in models:
                client.delete_model(m.id)
        while artifacts := client.list_artifacts().items:
            for a in artifacts:
                client.delete_artifact(a.id)
        while tags := client.list_tags(TagFilter()).items:
            for t in tags:
                client.delete_tag(t.id)
        while stacks := client.list_stacks().items:
            if len(stacks) <= 1:
                break
            if client.active_stack.name != "default":
                client.activate_stack("default")
            for s in stacks:
                if s.name != "default":
                    client.delete_stack(s.id, True)
        while stack_components := client.list_stack_components().items:
            if len(stack_components) <= 2:
                break
            for sc in stack_components:
                if not (
                    (
                        sc.type == StackComponentType.ORCHESTRATOR
                        or sc.type == StackComponentType.ARTIFACT_STORE
                    )
                    and sc.name == "default"
                ):
                    client.delete_stack_component(sc.id, sc.type)
