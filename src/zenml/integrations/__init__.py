#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""
The ZenML integrations module contains sub-modules for each integration that we
support. This includes orchestrators like Apache Airflow, visualization tools
like the ``facets`` library, as well as deep learning libraries like PyTorch.
"""

from zenml.integrations.airflow import AirflowIntegration  # noqa
from zenml.integrations.dash import DashIntegration  # noqa
from zenml.integrations.evidently import EvidentlyIntegration  # noqa
from zenml.integrations.facets import FacetsIntegration  # noqa
from zenml.integrations.gcp import GcpIntegration  # noqa
from zenml.integrations.graphviz import GraphvizIntegration  # noqa
from zenml.integrations.kubeflow import KubeflowIntegration  # noqa
from zenml.integrations.mlflow import MlflowIntegration  # noqa
from zenml.integrations.plotly import PlotlyIntegration  # noqa
from zenml.integrations.pytorch import PytorchIntegration  # noqa
from zenml.integrations.pytorch_lightning import (  # noqa
    PytorchLightningIntegration,
)
from zenml.integrations.sklearn import SklearnIntegration  # noqa
from zenml.integrations.tensorflow import TensorflowIntegration  # noqa
