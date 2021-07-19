from playground.base_pipeline import BasePipeline
from playground.preprocesser_step import PreprocesserStep
from playground.split_step import SplitStep


class SplitPipeline(BasePipeline):
    def __init__(self,
                 split_map,
                 param):
        super(SplitPipeline, self).__init__()

        self.split_step = SplitStep(split_map=split_map, unknown_param='asd')
        self.preprocesser_step = PreprocesserStep(param=param)

    def connect(self, datasource):
        self.split_step(input_data=datasource)
        self.preprocesser_step(input_data=self.split_step.outputs.output_data)

        return [self.split_step, self.preprocesser_step]
