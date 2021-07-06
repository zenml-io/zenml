from playground.client import Client
from playground.split_pipeline import SplitPipeline

client = Client()

split_pipeline = SplitPipeline(split_map={'train': 0.7, 'test': 0.3})

split_pipeline.run()

# client.run(split_pipeline)
