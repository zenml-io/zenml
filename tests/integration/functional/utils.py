from contextlib import contextmanager

from zenml.client import Client
from zenml.models import ModelFilterModel
from zenml.models.tag_models import TagFilterModel
from zenml.utils.string_utils import random_str


def sample_name(prefix: str = "aria") -> str:
    """Function to get random username."""
    return f"{prefix}-{random_str(4)}".lower()


@contextmanager
def model_killer():
    def cleanup():
        client = Client()
        models = client.list_models(ModelFilterModel(size=999))
        for model in models:
            try:
                client.delete_model(model.name)
            except KeyError:
                pass

    try:
        yield
    finally:
        cleanup()


@contextmanager
def tags_killer():
    def cleanup():
        client = Client()
        tags = client.list_tags(TagFilterModel(size=999))
        for tag in tags:
            try:
                client.delete_tag(tag.id)
            except KeyError:
                pass

    cleanup()
    try:
        yield
    finally:
        cleanup()
