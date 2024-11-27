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
"""ZenML integrations module.

The ZenML integrations module contains sub-modules for each integration that we
support. This includes orchestrators like Apache Airflow, visualization tools
like the ``facets`` library, as well as deep learning libraries like PyTorch.
"""
from zenml.integrations.airflow import AirflowIntegration  # noqa
from zenml.integrations.argilla import ArgillaIntegration  # noqa
from zenml.integrations.aws import AWSIntegration  # noqa
from zenml.integrations.azure import AzureIntegration  # noqa
from zenml.integrations.bentoml import BentoMLIntegration  # noqa
from zenml.integrations.bitbucket import BitbucketIntegration  # noqa
from zenml.integrations.databricks import DatabricksIntegration  # noqa
from zenml.integrations.comet import CometIntegration  # noqa
from zenml.integrations.deepchecks import DeepchecksIntegration  # noqa
from zenml.integrations.discord import DiscordIntegration  # noqa
from zenml.integrations.evidently import EvidentlyIntegration  # noqa
from zenml.integrations.facets import FacetsIntegration  # noqa
from zenml.integrations.feast import FeastIntegration  # noqa
from zenml.integrations.gcp import GcpIntegration  # noqa
from zenml.integrations.github import GitHubIntegration  # noqa
from zenml.integrations.gitlab import GitLabIntegration  # noqa
from zenml.integrations.great_expectations import (  # noqa
    GreatExpectationsIntegration,
)
from zenml.integrations.lightning import LightningIntegration  # noqa
from zenml.integrations.huggingface import HuggingfaceIntegration  # noqa
from zenml.integrations.hyperai import HyperAIIntegration  # noqa
from zenml.integrations.kaniko import KanikoIntegration  # noqa
from zenml.integrations.kubeflow import KubeflowIntegration  # noqa
from zenml.integrations.kubernetes import KubernetesIntegration  # noqa
from zenml.integrations.label_studio import LabelStudioIntegration  # noqa
from zenml.integrations.langchain import LangchainIntegration  # noqa
from zenml.integrations.lightgbm import LightGBMIntegration  # noqa

# from zenml.integrations.llama_index import LlamaIndexIntegration  # noqa
from zenml.integrations.mlflow import MlflowIntegration  # noqa
from zenml.integrations.modal import ModalIntegration  # noqa
from zenml.integrations.neptune import NeptuneIntegration  # noqa
from zenml.integrations.neural_prophet import NeuralProphetIntegration  # noqa
from zenml.integrations.numpy import NumpyIntegration  # noqa
from zenml.integrations.openai import OpenAIIntegration  # noqa
from zenml.integrations.pandas import PandasIntegration  # noqa
from zenml.integrations.pigeon import PigeonIntegration  # noqa
from zenml.integrations.pillow import PillowIntegration  # noqa
from zenml.integrations.polars import PolarsIntegration  # noqa
from zenml.integrations.prodigy import ProdigyIntegration  # noqa
from zenml.integrations.pycaret import PyCaretIntegration  # noqa
from zenml.integrations.pytorch import PytorchIntegration  # noqa
from zenml.integrations.pytorch_lightning import (  # noqa
    PytorchLightningIntegration,
)
from zenml.integrations.s3 import S3Integration  # noqa
from zenml.integrations.scipy import ScipyIntegration  # noqa
from zenml.integrations.seldon import SeldonIntegration  # noqa
from zenml.integrations.sklearn import SklearnIntegration  # noqa
from zenml.integrations.skypilot_aws import SkypilotAWSIntegration  # noqa
from zenml.integrations.skypilot_gcp import SkypilotGCPIntegration  # noqa
from zenml.integrations.skypilot_azure import SkypilotAzureIntegration  # noqa
from zenml.integrations.skypilot_lambda import SkypilotLambdaIntegration  # noqa
from zenml.integrations.skypilot_kubernetes import SkypilotKubernetesIntegration  # noqa
from zenml.integrations.slack import SlackIntegration  # noqa
from zenml.integrations.spark import SparkIntegration  # noqa
from zenml.integrations.tekton import TektonIntegration  # noqa
from zenml.integrations.tensorboard import TensorBoardIntegration  # noqa
from zenml.integrations.tensorflow import TensorflowIntegration  # noqa
from zenml.integrations.wandb import WandbIntegration  # noqa
from zenml.integrations.whylogs import WhylogsIntegration  # noqa
from zenml.integrations.xgboost import XgboostIntegration  # noqa
from zenml.integrations.vllm import VLLMIntegration  # noqa
