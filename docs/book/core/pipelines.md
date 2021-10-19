---
description: A pipeline is a logical sequence of tasks.
---

# Pipelines

Pipelines are functions. They are created by using decorators appropriate to the specific use case you have. The moment it is `run`, a pipeline is compiled and passed directly to the orchestrator, to be run in the orchestrator environment.

Within your repository, you will have one or more pipelines as part of your experimentation workflow. A ZenML pipeline is a sequence of tasks that execute in a specific order and yield artifacts. The artifacts are stored within the artifact store and indexed via the metadata store. Each individual task within a pipeline is known as a step. The standard pipelines \(like `SimplePipeline`\) within ZenML are designed to have easy interfaces to add pre-decided steps, with the order also pre-decided. Other sorts of pipelines can be created as well from scratch.

```python
@pipeline(name="my_pipeline")
def SplitPipeline(
    simple_step: Step[SimplestStepEver],
    data_step: Step[DataIngestionStep],
    split_step: Step[DistSplitStep],
    preprocessor_step: Step[InMemPreprocessorStep]
):

    data_step(input_random_number=simple_step.outputs["return_output"])
    split_step(input_artifact=data_step.outputs["output_artifact"])
    preprocessor_step(input_artifact=split_step.outputs["output_artifact"])


# Pipeline
pipeline = SplitPipeline(
    simple_step=SimplestStepEver(basic_param_1=2, basic_param_2="3"),
    data_step=DataIngestionStep(uri=os.getenv("test_data")),
    split_step=DistSplitStep(),
    preprocessor_step=InMemPreprocessorStep(),
)

pipeline_run = split_pipeline.run()
```

Pipelines consist of many [steps](steps.md#how-to-create-steps)..
