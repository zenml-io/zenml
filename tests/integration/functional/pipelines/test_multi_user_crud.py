import uuid

import pytest
from tests.integration.functional.zen_stores.utils import LoginContext

from zenml import pipeline, step
from zenml.client import Client
from zenml.config.global_config import GlobalConfiguration
from zenml.enums import StoreType
from zenml.models.v2.core.user import UserResponse


@step
def greet_step(name: str) -> str:
    return f"Welcome {name}"


@step
def crush_step():
    raise ValueError("Oh noooo...")


@pipeline
def pipeline_that_completes():
    greet_step("test")


@pipeline()
def pipeline_that_crushes():
    crush_step()


def submit_pipelines_programmatically(client: Client):
    pipeline_that_completes()

    try:
        pipeline_that_crushes()
    except RuntimeError:
        pass


def check_pipelines(client: Client, user_name: str):
    pipelines = client.list_pipelines(
        latest_run_status="completed", name="pipeline_that_completes"
    )

    assert pipelines.size == 1

    pipelines = client.list_pipelines(
        latest_run_status="failed", name="pipeline_that_crushes"
    )

    assert pipelines.size == 1

    pipelines = client.list_pipelines(
        name="pipeline_that_completes", latest_run_user=user_name
    )

    assert pipelines.size == 1

    pipelines = client.list_pipelines(
        name="pipeline_that_crushes", latest_run_user=user_name
    )

    assert pipelines.size == 1


def check_all_user_id_alternatives_work(client: Client, user: UserResponse):
    pipelines = client.list_pipelines(
        name="pipeline_that_completes", latest_run_user=user.id
    )

    assert pipelines.size == 1

    pipelines = client.list_pipelines(
        name="pipeline_that_completes", latest_run_user=str(user.id)
    )

    assert pipelines.size == 1

    pipelines = client.list_pipelines(
        name="pipeline_that_completes", latest_run_user=user.name
    )

    assert pipelines.size == 1


def test_multi_user_pipeline_executions():
    if GlobalConfiguration().zen_store.config.type != StoreType.REST:
        pytest.skip("Multi-user pipelines are supported only over REST.")

    client = Client()

    submit_pipelines_programmatically(client)

    check_pipelines(client, user_name="default")

    user = client.create_user(
        name=f"tester_{uuid.uuid4()}", password="1234", is_admin=True
    )

    with LoginContext(user_name=user.name, password="1234"):
        new_client = Client()

        submit_pipelines_programmatically(new_client)

        check_pipelines(new_client, user.name)

        check_all_user_id_alternatives_work(new_client, user=user)
