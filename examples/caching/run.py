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
import argparse
import sys
import textwrap

import numpy as np
import tensorflow as tf

from zenml.integrations.constants import TENSORFLOW
from zenml.pipelines import pipeline
from zenml.steps import BaseStepConfig, Output, step


class TrainerConfig(BaseStepConfig):
    """Trainer params

    Params:
        epochs: Amount of epochs for the training step
        lr: Learning rate to train with
    """

    epochs: int = 1
    lr: float = 0.001


@step
def importer_mnist() -> Output(
    X_train=np.ndarray, y_train=np.ndarray, X_test=np.ndarray, y_test=np.ndarray
):
    """Download the MNIST data store it as an artifact"""
    (X_train, y_train), (X_test, y_test) = tf.keras.datasets.mnist.load_data()
    return X_train, y_train, X_test, y_test


@step
def normalizer(
        X_train: np.ndarray, X_test: np.ndarray
) -> Output(X_train_normed=np.ndarray, X_test_normed=np.ndarray):
    """Normalize the values for all the images, so they are between 0 and 1"""
    X_train_normed = X_train / 255.0
    X_test_normed = X_test / 255.0
    return X_train_normed, X_test_normed


@step
def tf_trainer(
        config: TrainerConfig,
        X_train: np.ndarray,
        y_train: np.ndarray,
) -> tf.keras.Model:
    """Train a neural net from scratch to recognize MNIST digits return our
    model or the learner"""
    model = tf.keras.Sequential(
        [
            tf.keras.layers.Flatten(input_shape=(28, 28)),
            tf.keras.layers.Dense(10, activation="relu"),
            tf.keras.layers.Dense(10),
        ]
    )

    model.compile(
        optimizer=tf.keras.optimizers.Adam(config.lr),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
        metrics=["accuracy"],
    )

    model.fit(
        X_train,
        y_train,
        epochs=config.epochs,
    )

    # write model
    return model


@step
def tf_evaluator(
        X_test: np.ndarray,
        y_test: np.ndarray,
        model: tf.keras.Model,
) -> float:
    """Calculate the loss for the model for each epoch in a graph"""

    _, test_acc = model.evaluate(X_test, y_test, verbose=2)
    return test_acc


# Define the pipeline
@pipeline(required_integrations=[TENSORFLOW])
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
    parser = argparse.ArgumentParser(description='some information',
                                     usage='use "python %(prog)s --help" for more information',
                                     formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('--epoch', default=1, type=int,
                        help='Amount of epochs to train for - default is 1')
    parser.add_argument('--lr', default=0.001, type=float,
                        help='Learning rate to train with - default is 0.001')
    parser.add_argument('--mode', default='default', type=str,
                        choices=['default', 'invalidate', 'disable'],
                        help=textwrap.dedent('''\
                        Different configurations which show how the cache 
                        behaves within ZenML (and how to disable/invalidate it).
                        
                        `default` - Two consecutive pipeline runs where the 
                        first run is completely cached and all steps in the 
                        second run are skipped.

                        `invalidate` - Two consecutive pipeline runs with
                        cache invalidated through a change within the step 
                        configuration. 

                        `disable` - Two consecutive pipeline runs with one
                        of the steps being explicitly configured to 
                        disable cache.
                        '''))
    args = parser.parse_args()

    # Initialize a pipeline run
    pipeline_instance = mnist_pipeline(
        importer=importer_mnist(),
        normalizer=normalizer(),
        trainer=tf_trainer(config=TrainerConfig(epochs=args.epoch, lr=args.lr)),
        evaluator=tf_evaluator(),
    )

    # Run the pipeline once
    pipeline_instance.run()

    if args.mode == 'default':
        # Run the pipeline again - this time everything is cached (including the
        # model produced by the training step). As such this run should be much
        # faster as no step has to be run again
        pipeline_instance.run()

    elif args.mode == 'invalidate':
        # Initialize another pipeline instance with and arbitrarily small change
        # to the TrainerConfig. This change however will invalidate the cache
        # for this step
        pipeline_instance_2 = mnist_pipeline(
            importer=importer_mnist(),
            normalizer=normalizer(),
            trainer=tf_trainer(config=TrainerConfig(epochs=args.epoch,
                                                    lr=args.lr + 0.00000001)),
            evaluator=tf_evaluator(),
        )
        # Run the pipeline yet again - this time the cache for the training step
        # is disabled due to the changed configuration
        pipeline_instance_2.run()

    elif args.mode == 'decorator':
        # In this case we use a decorator to explicitly disable the cache on a
        # step. This means the output of this step will not be cached and all
        # subsequent steps will invalidate their caches.
        @step(enable_cache=False)
        def normalizer(
                X_train: np.ndarray, X_test: np.ndarray
        ) -> Output(X_train_normed=np.ndarray, X_test_normed=np.ndarray):
            """Normalize the values for all the images, so they are between
            0 and 1"""
            X_train_normed = X_train / 255.0
            X_test_normed = X_test / 255.0
            return X_train_normed, X_test_normed


        # Initialize the pipeline instance again with the new non-caching
        # normalizer step
        pipeline_instance_2 = mnist_pipeline(
            importer=importer_mnist(),
            normalizer=normalizer(),
            trainer=tf_trainer(config=TrainerConfig(epochs=args.epoch,
                                                    lr=args.lr)),
            evaluator=tf_evaluator(),
        )
        # Run the pipeline yet again - this time the cache for the training step
        # is disabled due to the changed configuration
        pipeline_instance_2.run()
