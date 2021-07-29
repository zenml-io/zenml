from playground.base_pipeline import BasePipeline


class SplitPipeline(BasePipeline):
    def connect(self, datasource):
        self.steps.split_step(input_data=datasource)
        self.steps.preprocesser_step(input_data=self.steps.split_step.outputs.output_data)
