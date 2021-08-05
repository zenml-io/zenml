# Option 1
from playground.artifacts.data_artifacts import CSVArtifact
from playground.steps.base_step import step
from playground.utils.annotations import Input, Output, Param


@step
def FunctionPreprocesserStep(input_data: Input[CSVArtifact],
                             output_data: Output[CSVArtifact],
                             param: Param[float]):
    data = input_data.read()
    param = None
    output_data.write(data)


# Option 2

from playground.steps.base_step import BaseStep


class ClassPreprocesserStep(BaseStep):
    def process(self,
                input_data: Input[CSVArtifact],
                output_data: Output[CSVArtifact],
                param: Param[float]):
        data = input_data.read()
        param = None
        output_data.write(data)
