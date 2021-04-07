# Classification with 59M samples

In this tutorial, we'll go through the step-by-step process of building a simple feedforward classifier trained on a public BigQuery datasource.

```text
This tutorial is adapted **from the blog post:** [Deep Learning on 33,000,000 data points using a few lines of YAML](https://blog.maiot.io/deep_learning_33_million_with_few_lines_yaml/)
```

tldr; One can utilize the [Dataflow Processing Backend](../backends/processing-backends.md).

```python
from zenml.backends.processing import ProcessingDataFlowBackend

training_pipeline = TrainingPipeline(name='distributed_dataflow')

# add steps
...

# configure steps
processing_backend = ProcessingDataFlowBackend(project='GCP_PROJECT')

# Run the pipeline
training_pipeline.run(
    backends=[processing_backend],
)
```

Full code example can be found [here](https://github.com/maiot-io/zenml/blob/main/examples/gcp_dataflow_processing)

Detailed tutorial to follow! Check out the [GitHub repo](https://github.com/maiot-io/zenml) to get updates!

