#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""PyCaret materializer."""

from typing import (
    Any,
    Type,
)

from catboost import CatBoostClassifier, CatBoostRegressor  # type: ignore
from lightgbm import LGBMClassifier, LGBMRegressor
from pycaret.classification import load_model, save_model  # type: ignore
from sklearn.discriminant_analysis import (
    LinearDiscriminantAnalysis,
    QuadraticDiscriminantAnalysis,
)
from sklearn.ensemble import (
    AdaBoostClassifier,
    AdaBoostRegressor,
    BaggingRegressor,
    ExtraTreesClassifier,
    ExtraTreesRegressor,
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.gaussian_process import GaussianProcessClassifier
from sklearn.kernel_ridge import KernelRidge
from sklearn.linear_model import (
    ARDRegression,
    BayesianRidge,
    ElasticNet,
    HuberRegressor,
    Lars,
    Lasso,
    LassoLars,
    LinearRegression,
    LogisticRegression,
    OrthogonalMatchingPursuit,
    PassiveAggressiveRegressor,
    RANSACRegressor,
    Ridge,
    RidgeClassifier,
    SGDClassifier,
    TheilSenRegressor,
)
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.neural_network import MLPClassifier, MLPRegressor
from sklearn.svm import SVC, SVR
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from xgboost import XGBClassifier, XGBRegressor

from zenml.enums import ArtifactType
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.utils import io_utils


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
            A PyCaret model.
        """
        with self.get_temporary_directory(delete_at_exit=True) as temp_dir:
            io_utils.copy_dir(self.uri, temp_dir)
            model = load_model(temp_dir)
            return model

    def save(self, model: Any) -> None:
        """Writes a PyCaret model to the artifact store.

        Args:
            model: Any of the supported models.
        """
        with self.get_temporary_directory(delete_at_exit=True) as temp_dir:
            save_model(model, temp_dir.name)
            io_utils.copy_dir(temp_dir.name, self.uri)
