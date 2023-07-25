from pydantic import BaseConfig
from scipy.stats import uniform
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier

from zenml.config import DockerSettings
from zenml.integrations.constants import (
    AWS,
    EVIDENTLY,
    KUBEFLOW,
    KUBERNETES,
    MLFLOW,
    SKLEARN,
    SLACK,
)
from zenml.model_registries.base_model_registry import ModelVersionStage

NOTIFY_ON_SUCCESS = False
NOTIFY_ON_FAILURE = False


class MetaConfig(BaseConfig):
    pipeline_name_training = "e2e_example_training"
    pipeline_name_batch_inference = "e2e_example_batch_inference"
    mlflow_model_name = "e2e_example_model"
    target_env = ModelVersionStage.STAGING
    target_column = "target"
    supported_models = {
        "LogisticRegression": {
            "class": LogisticRegression,
            "search_grid": dict(
                C=uniform(loc=0, scale=4),
                penalty=["l2", "none"],
                max_iter=range(10, 1000),
            ),
        },
        "DecisionTreeClassifier": {
            "class": DecisionTreeClassifier,
            "search_grid": dict(
                criterion=["gini", "entropy"],
                max_depth=[2, 4, 6, 8, 10, 12],
                min_samples_leaf=range(1, 10),
            ),
        },
    }
    default_model_config = {
        "class": DecisionTreeClassifier,
        "params": dict(
            criterion="gini",
            max_depth=5,
            min_samples_leaf=3,
        ),
    }


DOCKER_SETTINGS = DockerSettings(
    required_integrations=[
        AWS,
        EVIDENTLY,
        KUBEFLOW,
        KUBERNETES,
        MLFLOW,
        SKLEARN,
        SLACK,
    ],
)
