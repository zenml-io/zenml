from typing import Text, Dict, Any, Optional

from tfx.dsl.components.base.executor_spec import ExecutorClassSpec
from tfx.types import standard_artifacts, Channel
from tfx.types.component_spec import ComponentSpec, ExecutionParameter, \
    ChannelParameter
from tfx.components.transform.component import Transform

from zenml.components.data_gen.constants import DATA_SPLIT_NAME
from zenml.components.data_gen.executor import DataExecutor
from zenml.standards.standard_keys import StepKeys


class SimpleTransformSpec(ComponentSpec):
    PARAMETERS = {
        StepKeys.NAME: ExecutionParameter(type=Text),
        StepKeys.SOURCE: ExecutionParameter(type=Text),
        StepKeys.ARGS: ExecutionParameter(type=Dict[Text, Any]),
    }
    INPUTS = {}
    OUTPUTS = {
        DATA_SPLIT_NAME: ChannelParameter(type=standard_artifacts.Examples)
    }


class SimpleTransform(Transform):
    SPEC_CLASS = SimpleTransformSpec
    EXECUTOR_SPEC = ExecutorClassSpec(DataExecutor)

    def __init__(self,
                 name: Text,
                 source: Text,
                 source_args: Dict[Text, Any],
                 instance_name: Optional[Text] = None,
                 examples: Optional[ChannelParameter] = None):
        """
        Interface for all SimpleTransform components, the main component responsible
        for reading data and converting to TFRecords. This is how we handle
        versioning data for now.

        Args:
            name: name of datasource.
            source:
            source_args:
            instance_name:
            examples:
        """
        examples = examples or Channel(type=standard_artifacts.Examples)

        # Initiate the spec and create instance
        spec = self.SPEC_CLASS(name=name,
                               source=source,
                               args=source_args,
                               examples=examples)

        super(SimpleTransform, self).__init__(spec=spec,
                                      instance_name=instance_name)
