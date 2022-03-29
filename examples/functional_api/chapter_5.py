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

import os
import re

import numpy as np
import tensorflow as tf
from sklearn.base import ClassifierMixin
from sklearn.linear_model import LogisticRegression
from sqlalchemy import Column, Float, Integer, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from zenml.integrations.constants import SKLEARN, TENSORFLOW
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.pipelines import pipeline
from zenml.repository import Repository
from zenml.steps import BaseStepConfig, Output, step

# Path to a pip requirements file that contains requirements necessary to run
# the pipeline
requirements_file = os.path.join(
    os.path.dirname(__file__), "chapter_5_requirements.txt"
)

Base = declarative_base()


class Floats(Base):
    __tablename__ = "my_floats"

    id = Column(Integer, primary_key=True)
    value = Column(Float, nullable=False)


class SQLALchemyMaterializerForSQLite(BaseMaterializer):
    """Read/Write float to sqlalchemy table."""

    ASSOCIATED_TYPES = (float,)

    def __init__(self, artifact):
        super().__init__(artifact)
        # connection
        sqlite_filepath = os.path.join(artifact.uri, "database")
        engine = create_engine(f"sqlite:///{sqlite_filepath}")

        # create metadata
        Base.metadata.create_all(engine)

        # create session
        Session = sessionmaker(bind=engine)
        self.session = Session()

        # Every artifact has a URI with a unique integer ID
        self.float_id = int(re.search(r"\d+", artifact.uri).group())

    def handle_input(self, data_type) -> float:
        """Reads float from a table"""
        super().handle_input(data_type)

        # query data
        return (
            self.session.query(Floats)
            .filter(Floats.id == self.float_id)
            .first()
        ).value

    def handle_return(self, data: float):
        """Stores float in a SQLAlchemy Table"""
        super().handle_return(data)
        my_float = Floats(id=self.float_id, value=data)
        self.session.add_all([my_float])
        self.session.commit()


class TrainerConfig(BaseStepConfig):
    """Trainer params"""

    epochs: int = 1
    gamma: float = 0.7
    lr: float = 0.001


@step
def importer_mnist() -> Output(
    X_train=np.ndarray, y_train=np.ndarray, X_test=np.ndarray, y_test=np.ndarray
):
    """Download the MNIST data and store it as an artifact"""
    (X_train, y_train), (
        X_test,
        y_test,
    ) = tf.keras.datasets.mnist.load_data()
    return X_train, y_train, X_test, y_test


@step
def normalize_mnist(
    X_train: np.ndarray, X_test: np.ndarray
) -> Output(X_train_normed=np.ndarray, X_test_normed=np.ndarray):
    """Normalize the values for all the images so they are between 0 and 1"""
    X_train_normed = X_train / 255.0
    X_test_normed = X_test / 255.0
    return X_train_normed, X_test_normed


@step
def sklearn_trainer(
    config: TrainerConfig,
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> ClassifierMixin:
    """Train SVC from sklearn."""
    clf = LogisticRegression(penalty="l1", solver="saga", tol=0.1)
    clf.fit(X_train.reshape((X_train.shape[0], -1)), y_train)
    return clf


@step
def sklearn_evaluator(
    X_test: np.ndarray,
    y_test: np.ndarray,
    model: ClassifierMixin,
) -> float:
    """Calculate accuracy score with classifier."""

    test_acc = model.score(X_test.reshape((X_test.shape[0], -1)), y_test)
    return test_acc


@pipeline(
    required_integrations=[SKLEARN, TENSORFLOW],
    requirements_file=requirements_file,
)
def mnist_pipeline(
    importer,
    normalizer,
    trainer,
    evaluator,
):
    # Link all the steps artifacts together
    X_train, y_train, X_test, y_test = importer()
    X_trained_normed, X_test_normed = normalizer(X_train=X_train, X_test=X_test)
    model = trainer(X_train=X_trained_normed, y_train=y_train)
    evaluator(X_test=X_test_normed, y_test=y_test, model=model)


if __name__ == "__main__":

    # Initialize a new pipeline run
    scikit_p = mnist_pipeline(
        importer=importer_mnist(),
        normalizer=normalize_mnist(),
        trainer=sklearn_trainer(config=TrainerConfig()),
        evaluator=sklearn_evaluator().with_return_materializers(
            SQLALchemyMaterializerForSQLite
        ),
    )

    # Run the new pipeline
    scikit_p.run()

    # Post-execution
    repo = Repository()
    p = repo.get_pipeline(pipeline_name="mnist_pipeline")
    print(f"Pipeline `mnist_pipeline` has {len(p.runs)} run(s)")
    eval_step = p.runs[-1].get_step("evaluator")
    val = eval_step.output.read(float, SQLALchemyMaterializerForSQLite)
    print(f"The evaluator stored the value: {val} in a SQLite database!")
