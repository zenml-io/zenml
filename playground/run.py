from playground.split_pipeline import SplitPipeline

uri = '/home/baris/Maiot/zenml/local_test/new_zenml/db'

# Parameters
param = 1
split_map = {'train': 0.7, 'test': 0.3}

# Pipeline
split_pipeline = SplitPipeline(split_map=split_map,
                               param=param)
split_pipeline.run(None)
