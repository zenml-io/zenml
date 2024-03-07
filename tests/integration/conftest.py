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
                client.delete_pipeline(p.id)
        while deployments := client.list_deployments().items:
            for d in deployments:
                client.delete_deployment(str(d.id))
        while models := client.list_models().items:
            for m in models:
                client.delete_model(m.id)
        while artifacts := client.list_artifacts().items:
            for a in artifacts:
                client.delete_artifact(a.id)
        while tags := client.list_tags(TagFilter()).items:
            for t in tags:
                client.delete_tag(t.id)
