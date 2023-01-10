import pytest

from zenml.client import Client
from zenml.models import (
    ProjectRequestModel,
    ProjectResponseModel,
    UserRequestModel,
    UserResponseModel,
)
from zenml.utils.string_utils import random_str


def sample_name(prefix: str = "aria") -> str:
    """Function to get random username."""
    return f"{prefix}_{random_str(4)}"


@pytest.fixture
def sample_project() -> "ProjectResponseModel":
    """Function to create a sample project."""
    client = Client()
    new_project = ProjectRequestModel(name=sample_name("sample_prj"))
    created_sample_project = client.zen_store.create_project(new_project)
    yield created_sample_project
    # In case the test didn't delete the project it is cleaned up here
    try:
        client.zen_store.delete_project(created_sample_project.id)
    except KeyError:
        pass


@pytest.fixture
def sample_user() -> "UserResponseModel":
    """Function to create a sample user."""
    client = Client()
    new_user = UserRequestModel(
        name=sample_name("sample_user"), password=random_str(8)
    )
    created_sample_user = client.zen_store.create_user(new_user)
    yield created_sample_user
    # In case the test didn't delete the user it is cleaned up here
    try:
        client.zen_store.delete_user(created_sample_user.id)
    except KeyError:
        pass
