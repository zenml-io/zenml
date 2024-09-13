# zenml.post_execution package

## Submodules

## zenml.post_execution.pipeline module

Implementation of the post-execution pipeline.

### zenml.post_execution.pipeline.get_pipeline(pipeline: str) → [PipelineResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline.PipelineResponse) | None

(Deprecated) Fetches a pipeline model.

Args:
: pipeline: The name of the pipeline.

Returns:
: The pipeline model.

### zenml.post_execution.pipeline.get_pipelines() → List[[PipelineResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline.PipelineResponse)]

(Deprecated) Fetches all pipelines in the active workspace.

Returns:
: A list of pipeline models.

## zenml.post_execution.pipeline_run module

Implementation of the post-execution pipeline run class.

### zenml.post_execution.pipeline_run.get_run(name: str) → [PipelineRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunResponse)

(Deprecated) Fetches the run with the given name.

Args:
: name: The name of the run to fetch.

Returns:
: The run with the given name.

### zenml.post_execution.pipeline_run.get_unlisted_runs() → List[[PipelineRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunResponse)]

(Deprecated) Fetches the 50 most recent unlisted runs.

Unlisted runs are runs that are not associated with any pipeline.

Returns:
: A list of the 50 most recent unlisted runs.

## Module contents

Deprecated post-execution utility functions.

### zenml.post_execution.get_pipeline(pipeline: str) → [PipelineResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline.PipelineResponse) | None

(Deprecated) Fetches a pipeline model.

Args:
: pipeline: The name of the pipeline.

Returns:
: The pipeline model.

### zenml.post_execution.get_pipelines() → List[[PipelineResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline.PipelineResponse)]

(Deprecated) Fetches all pipelines in the active workspace.

Returns:
: A list of pipeline models.

### zenml.post_execution.get_run(name: str) → [PipelineRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunResponse)

(Deprecated) Fetches the run with the given name.

Args:
: name: The name of the run to fetch.

Returns:
: The run with the given name.

### zenml.post_execution.get_unlisted_runs() → List[[PipelineRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunResponse)]

(Deprecated) Fetches the 50 most recent unlisted runs.

Unlisted runs are runs that are not associated with any pipeline.

Returns:
: A list of the 50 most recent unlisted runs.
