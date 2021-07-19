from playground.artifacts import DataArtifact, Input, Output
from playground.base_step import BaseStep


class PreprocesserStep(BaseStep):
    def __init__(self, param: float):
        self.param = param

        super(PreprocesserStep, self).__init__()

    def process(self,
                input_data: Input[DataArtifact],
                output_data: Output[DataArtifact]):
        self.param = 0.3
