# Option 1
from playground.artifacts import CSVArtifact
from playground.utils.annotations import Input, Output, Param
from playground.steps.base_step import step


@step
def FunctionPreprocesserStep(input_data: Input[CSVArtifact],
                             output_data: Output[CSVArtifact],
                             param: Param[float]):
    input_data.read()
    param = None
    output_data.write()


# Option 2

from playground.steps.base_step import BaseStep


class ClassPreprocesserStep(BaseStep):
    def connect(self,
                input_data: Input[CSVArtifact],
                output_data: Output[CSVArtifact],
                param: Param[float]):
        input_data.read()
        param = None
        output_data.write()
