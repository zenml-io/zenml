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
from typing import Type, Any, Union
import tempfile

from pycaret.classification import save_model, load_model
from zenml.enums import ArtifactType
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.utils import io_utils

# Classification models supported by PyCaret
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.tree import DecisionTreeClassifier
from sklearn.linear_model import SGDClassifier
from sklearn.svm import SVC
from sklearn.gaussian_process import GaussianProcessClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.linear_model import RidgeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.discriminant_analysis import QuadraticDiscriminantAnalysis
from sklearn.ensemble import AdaBoostClassifier
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.ensemble import ExtraTreesClassifier
from xgboost import XGBClassifier
from catboost import CatBoostClassifier
from lightgbm import LGBMClassifier

from sklearn.linear_model import LinearRegression
from sklearn.linear_model import Lasso
from sklearn.linear_model import Ridge
from sklearn.linear_model import ElasticNet
from sklearn.linear_model import Lars
from sklearn.linear_model import LassoLars
from sklearn.linear_model import OrthogonalMatchingPursuit
from sklearn.linear_model import BayesianRidge
from sklearn.linear_model import ARDRegression
from sklearn.linear_model import PassiveAggressiveRegressor
from sklearn.linear_model import RANSACRegressor
from sklearn.linear_model import TheilSenRegressor
from sklearn.linear_model import HuberRegressor
from sklearn.kernel_ridge import KernelRidge
from sklearn.svm import SVR
from sklearn.neighbors import KNeighborsRegressor
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.ensemble import AdaBoostRegressor
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.neural_network import MLPRegressor
from xgboost import XGBRegressor
from catboost import CatBoostRegressor
from sklearn.ensemble import BaggingRegressor
from sklearn.ensemble import AdaBoostRegressor
from lightgbm import LGBMRegressor


class PyCaretMaterializer(BaseMaterializer):
    """Materializer to read/write PyCaret models."""

    ASSOCIATED_TYPES = (
        # Classification
        LogisticRegression,
        KNeighborsClassifier,
        GaussianNB,
        DecisionTreeClassifier,
        SGDClassifier,
        SVC,
        GaussianProcessClassifier,
        MLPClassifier,
        RidgeClassifier,
        RandomForestClassifier,
        QuadraticDiscriminantAnalysis,
        AdaBoostClassifier,
        GradientBoostingClassifier,
        LinearDiscriminantAnalysis,
        ExtraTreesClassifier,
        XGBClassifier,
        CatBoostClassifier,
        LGBMClassifier,
        # Regression
        LinearRegression,
        Lasso,
        Ridge,
        ElasticNet,
        Lars,
        LassoLars,
        OrthogonalMatchingPursuit,
        BayesianRidge,
        ARDRegression,
        PassiveAggressiveRegressor,
        RANSACRegressor,
        TheilSenRegressor,
        HuberRegressor,
        KernelRidge,
        SVR,
        KNeighborsRegressor,
        DecisionTreeRegressor,
        RandomForestRegressor,
        ExtraTreesRegressor,
        AdaBoostRegressor,
        GradientBoostingRegressor,
        MLPRegressor,
        XGBRegressor,
        CatBoostRegressor,
        BaggingRegressor,
        AdaBoostRegressor,
        LGBMRegressor,
    )
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.MODEL

    def load(self, data_type: Type[Any]) -> Any:
        """Reads and returns a PyCaret model after copying it to temporary path.

        Args:
            data_type: The type of the data to read.

        Returns:
            A PyCaret  model.
        """
        super().load(data_type)

        # Create a temporary directory to store the model
        temp_dir = tempfile.TemporaryDirectory()

        # Copy from artifact store to temporary directory
        io_utils.copy_dir(self.uri, temp_dir.name)

        # Load the model from the temporary directory
        model = load_model(temp_dir.name)

        # Cleanup and return
        fileio.rmtree(temp_dir.name)

        return model

    def save(self, model: Any) -> None:
        """Writes a PyCaret model to the artifact store.

        Args:
            model: Any of the supported models.
        """
        super().save(model)

        # Create a temporary directory to store the model
        temp_dir = tempfile.TemporaryDirectory()
        save_model(model, temp_dir.name)
        io_utils.copy_dir(temp_dir.name, self.uri)

        # Remove the temporary directory
        fileio.rmtree(temp_dir.name)
