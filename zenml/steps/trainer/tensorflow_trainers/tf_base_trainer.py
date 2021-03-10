#  Copyright (c) maiot GmbH 2020. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

from zenml.steps.trainer import BaseTrainerStep


class TFBaseTrainerStep(BaseTrainerStep):
    """
    Base class for all Tensorflow-based trainer steps. All tensorflow based
    trainings should use this as the base class. An example is available
    with tf_ff_trainer.FeedForwardTrainer.
    """

    @staticmethod
    def _get_ce_eval_tf_examples_fn(model, tf_transform_output):
        """
        Serving evaluation signature definition. Override this function to
        define a custom model endpoint used for evaluation at serving time.

        Args:
            model: Trained model, output of the model_fn.
            tf_transform_output: Output of the preceding Preprocessing
             component.

        Returns:
            eval_examples_fn: A @tf.function annotated callable that takes
             in a serialized tf.train.Example, parses it and serves the model
             output of this Example as evaluation. In Tensorflow Extended,
             such a mechanism is called a signature; for an example
             implementation of this signature, see a ZenML derived TrainerStep
             class.
        """
        pass

    @staticmethod
    def _get_serve_tf_examples_fn(model, tf_transform_output):
        """
        Defines a serving prediction signature. Override this function to
        create a custom model endpoint that can be used for prediction at
        serving time.

        Args:
            model: Trained model, output of the model_fn.
            tf_transform_output: Output of the preceding Preprocessing
             component.

        Returns:
            serve_examples_fn: A @tf.function annotated callable that takes
             in a serialized tf.train.Example, parses it and serves the model
             output of this Example as a prediction. In Tensorflow Extended,
             such a mechanism is called a signature; for an example
             implementation of this signature, see a ZenML derived TrainerStep
             class.
        """
        pass


