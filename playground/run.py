from playground.preprocesser_step import PreprocesserStep
from playground.split_pipeline import SplitPipeline
from playground.split_step import SplitStep

# Parameters
param = 1.0
split_map = 0.6

placeholder_datasource = None

# Steps
split_step = SplitStep(split_map=split_map)
preprocesser_step = PreprocesserStep(param=param)

# Pipeline
split_pipeline = SplitPipeline(split_step=split_step,
                               preprocesser_step=preprocesser_step)

split_pipeline.run(placeholder_datasource)
