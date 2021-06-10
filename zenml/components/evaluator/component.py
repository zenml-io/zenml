from typing import Optional
from typing import Text, Dict, Any

from tfx import types
from tfx.dsl.components.base import base_component
from tfx.dsl.components.base import executor_spec
from tfx.types.component_spec import ChannelParameter
from tfx.types.component_spec import ComponentSpec
from tfx.types.component_spec import ExecutionParameter
from tfx.types.standard_artifacts import Examples, Model, Schema, \
    ModelEvaluation, ModelBlessing

from zenml.components.evaluator import constants
from zenml.components.evaluator import executor


class ZenMLEvaluatorSpec(ComponentSpec):
    PARAMETERS = {constants.SOURCE: ExecutionParameter(type=Text),
                  constants.ARGS: ExecutionParameter(Text)}

    INPUTS = {
        constants.EXAMPLES: ChannelParameter(type=Examples),
        constants.MODEL: ChannelParameter(type=Model, optional=True),
        constants.BASELINE_MODEL: ChannelParameter(type=Model, optional=True),
        constants.SCHEMA: ChannelParameter(type=Schema, optional=True)
    }

    OUTPUTS = {
        constants.EVALUATION: ChannelParameter(type=ModelEvaluation),
        constants.BLESSING: ChannelParameter(type=ModelBlessing,
                                             optional=True),
    }


class Evaluator(base_component.BaseComponent):
    """
    A new adapted version version of the TFX Evaluator component.

    In contrast to the original evaluator component, it utilizes a ZenML
    EvaluatorStep and allows the model agnostic evaluation.
    """
    SPEC_CLASS = ZenMLEvaluatorSpec
    EXECUTOR_SPEC = executor_spec.ExecutorClassSpec(executor.Executor)

    def __init__(
            self,
            source: Text,
            source_args: Dict[Text, Any],
            examples: types.Channel = None,
            model: types.Channel = None,
            baseline_model: Optional[types.Channel] = None,
            blessing: Optional[types.Channel] = None,
            output: Optional[types.Channel] = None,
            schema: Optional[types.Channel] = None):
        # Create the output artifact if not provided
        evaluation = output or types.Channel(type=ModelEvaluation)
        blessing = blessing or types.Channel(type=ModelBlessing)

        # Create the spec
        spec = ZenMLEvaluatorSpec(source=source,
                                  args=source_args,
                                  examples=examples,
                                  model=model,
                                  baseline_model=baseline_model,
                                  blessing=blessing,
                                  schema=schema,
                                  evaluation=evaluation)
        super(Evaluator, self).__init__(spec=spec)
