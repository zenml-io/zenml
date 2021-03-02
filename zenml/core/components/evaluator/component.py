from typing import List, Text
from typing import Optional

import tensorflow_model_analysis as tfma
from tfx import types
from tfx.dsl.components.base import base_component
from tfx.dsl.components.base import executor_spec
from tfx.types import standard_artifacts
from tfx.types.component_spec import ChannelParameter
from tfx.types.component_spec import ComponentSpec
from tfx.types.component_spec import ExecutionParameter
from tfx.utils import json_utils

from zenml.core.components.evaluator import constants
from zenml.core.components.evaluator import executor


class ZenMLEvaluatorSpec(ComponentSpec):
    INPUTS = {
        constants.EXAMPLES: ChannelParameter(type=standard_artifacts.Examples),
        constants.MODEL: ChannelParameter(type=standard_artifacts.Model,
                                          optional=True),
        constants.SCHEMA: ChannelParameter(type=standard_artifacts.Schema,
                                           optional=True)}
    OUTPUTS = {
        constants.EVALUATION: ChannelParameter(
            type=standard_artifacts.ModelEvaluation)}

    PARAMETERS = {
        constants.EVAL_CONFIG: ExecutionParameter(type=tfma.EvalConfig,
                                                  optional=True),
        constants.EXAMPLE_SPLITS: ExecutionParameter(type=(str, Text),
                                                     optional=True),
        constants.MODULE_FILE: ExecutionParameter(type=(str, Text),
                                                  optional=True),
        constants.MODULE_PATH: ExecutionParameter(type=(str, Text),
                                                  optional=True)}


class Evaluator(base_component.BaseComponent):
    SPEC_CLASS = ZenMLEvaluatorSpec
    EXECUTOR_SPEC = executor_spec.ExecutorClassSpec(executor.Executor)

    def __init__(
            self,
            examples: types.Channel = None,
            model: types.Channel = None,
            example_splits: Optional[List[Text]] = None,
            output: Optional[types.Channel] = None,
            instance_name: Optional[Text] = None,
            eval_config: Optional[tfma.EvalConfig] = None,
            schema: Optional[types.Channel] = None,
            module_file: Optional[Text] = None,
            module_path: Optional[Text] = None):

        evaluation = output or types.Channel(
            type=standard_artifacts.ModelEvaluation)

        spec = ZenMLEvaluatorSpec(
            examples=examples,
            model=model,
            schema=schema,
            evaluation=evaluation,
            example_splits=json_utils.dumps(example_splits),
            eval_config=eval_config,
            module_file=module_file,
            module_path=module_path)
        super(Evaluator, self).__init__(spec=spec, instance_name=instance_name)
