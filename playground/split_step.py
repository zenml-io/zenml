from typing import Text, Dict

from playground.artifacts import DataArtifact, Input, Output
from playground.base_step import BaseStep


def lint_split_map(split_map: Dict[Text, float]):
    """Small utility to lint the split_map"""
    if len(split_map) <= 1:
        raise AssertionError(
            'Please specify more than 1 split name in the '
            'split_map!')

    if not all(isinstance(v, (int, float)) for v in split_map.values()):
        raise AssertionError("Only int or float values are allowed when "
                             "specifying a random split!")


class SplitStep(BaseStep):
    def __init__(self,
                 split_map: Dict[Text, float],
                 unknown_param,
                 some_ratio: float = 0.3):
        lint_split_map(split_map)
        self.split_map = split_map

        super(SplitStep, self).__init__()

    def process(self,
                input_data: Input[DataArtifact],
                output_data: Output[DataArtifact]):
        self.split_map = 'some logics'
