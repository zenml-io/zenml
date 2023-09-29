from contextlib import contextmanager

from zenml.client import Client
from zenml.models import ModelFilterModel
from zenml.utils.string_utils import random_str


def sample_name(prefix: str = "aria") -> str:
    """Function to get random username."""
    return f"{prefix}-{random_str(4)}".lower()


@contextmanager
def model_killer():
    try:
        yield
    finally:
        client = Client()
        models = client.list_models(ModelFilterModel(size=999))
        for model in models:
            try:
                client.delete_model(model.name)
            except KeyError:
                pass
