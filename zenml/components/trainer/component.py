from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from typing import Any, Dict, Optional, Text, Union, List

from tfx import types
from tfx.dsl.components.base import base_component
from tfx.dsl.components.base import executor_spec
from tfx.orchestration import data_types
from tfx.types.component_spec import ChannelParameter
from tfx.types.component_spec import ComponentSpec
from tfx.types.component_spec import ExecutionParameter
from tfx.types.standard_artifacts import Examples, TransformGraph, Schema, \
    Model, ModelRun, HyperParameters
from tfx.utils import json_utils

from zenml.components.trainer import constants
from zenml.components.trainer.executor import ZenMLTrainerExecutor


class ZenMLTrainerSpec(ComponentSpec):
    PARAMETERS = {
        constants.RUN_FN: ExecutionParameter(type=(str, Text), optional=True),
        constants.CUSTOM_CONFIG: ExecutionParameter(type=(str, Text),
                                                    optional=True),
    }
    INPUTS = {
        constants.EXAMPLES: ChannelParameter(type=Examples),
        constants.SCHEMA: ChannelParameter(type=Schema,
                                           optional=True),
        constants.BASE_MODEL: ChannelParameter(type=Model,
                                               optional=True),
        constants.TRANSFORM_GRAPH: ChannelParameter(type=TransformGraph,
                                                    optional=True),
        constants.HYPERPARAMETERS: ChannelParameter(type=HyperParameters,
                                                    optional=True),
    }
    OUTPUTS = {
        constants.MODEL: ChannelParameter(type=Model),
        constants.MODEL_RUN: ChannelParameter(type=ModelRun),
        constants.TEST_RESULTS: ChannelParameter(type=Examples)
    }


class Trainer(base_component.BaseComponent):
    """
    A slightly adjusted version of the TFX Trainer Component. It features an
    additional output artifact to save the test results in.
    """
    SPEC_CLASS = ZenMLTrainerSpec
    EXECUTOR_SPEC = executor_spec.ExecutorClassSpec(ZenMLTrainerExecutor)

    def __init__(
            self,
            examples: types.Channel = None,
            transformed_examples: Optional[types.Channel] = None,
            transform_graph: Optional[types.Channel] = None,
            schema: Optional[types.Channel] = None,
            base_model: Optional[types.Channel] = None,
            hyperparameters: Optional[types.Channel] = None,
            run_fn: Optional[Union[Text, data_types.RuntimeParameter]] = None,
            custom_config: Optional[Dict[Text, Any]] = None,
            custom_executor_spec: Optional[executor_spec.ExecutorSpec] = None,
            output: Optional[types.Channel] = None,
            model_run: Optional[types.Channel] = None,
            test_results: Optional[types.Channel] = None,
            instance_name: Optional[Text] = None):

        if bool(examples) == bool(transformed_examples):
            raise ValueError("Exactly one of 'example' or "
                             "'transformed_example' must be supplied.")

        if transformed_examples and not transform_graph:
            raise ValueError("If 'transformed_examples' is supplied, "
                             "'transform_graph' must be supplied too.")

        examples = examples or transformed_examples
        output = output or types.Channel(type=Model)
        model_run = model_run or types.Channel(type=ModelRun)
        test_results = test_results or types.Channel(type=Examples)

        spec = ZenMLTrainerSpec(examples=examples,
                                transform_graph=transform_graph,
                                schema=schema,
                                base_model=base_model,
                                hyperparameters=hyperparameters,
                                run_fn=run_fn,
                                custom_config=json_utils.dumps(custom_config),
                                model=output,
                                model_run=model_run,
                                test_results=test_results)

        super(Trainer, self).__init__(spec=spec,
                                      custom_executor_spec=custom_executor_spec,
                                      instance_name=instance_name)
