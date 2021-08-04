# Option 1
from playground.artifacts.data_artifacts import CSVArtifact
from playground.steps.base_step import step
from playground.utils.annotations import Input, Output, Param


@step
def FunctionSplitStep(input_data: Input[CSVArtifact],
                      output_data: Output[CSVArtifact],
                      split_map: Param[float]):
    input_data.read()
    split_map = None
    output_data.write()


# Option 2

from playground.steps.base_step import BaseStep


class ClassSplitStep(BaseStep):
    def process(self,
                input_data: Input[CSVArtifact],
                output_data: Output[CSVArtifact],
                split_map: Param[float]):
        data = input_data.read()
        split_map = None
        output_data.write(data)
