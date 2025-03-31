---
description: Interacting with your ZenML instance programmatically
---

# Client

The ZenML Python Client provides a programmatic interface to interact with your ZenML instance. It allows you to fetch, update, or create various resources like pipelines, runs, stacks, and more from your Python code.

## Understanding the ZenML Client

The ZenML Client acts as a bridge between your code and the ZenML server, enabling you to:

- Access pipeline runs, artifacts, and metadata
- Manage stacks and stack components
- Query and filter resources
- Perform administrative operations

## Getting Started with the Client

Using the ZenML Client is straightforward:

```python
from zenml.client import Client

# Initialize the client
client = Client()

# Now you can interact with your ZenML resources
```

## Working with Resources

The Client provides access to the following core ZenML resources:

### Pipelines and Runs

```python
# List your pipeline runs (most recent first)
runs = client.list_pipeline_runs(
    sort_by="desc:start_time",
    size=10
)

# Get a specific pipeline run by ID or name
run = client.get_pipeline_run("my-pipeline-run-name")

# Get details about a specific pipeline
pipeline = client.get_pipeline("my-pipeline-name")
```

### Artifacts

```python
# List artifacts
artifacts = client.list_artifacts(size=10)

# Get a specific artifact by ID
artifact = client.get_artifact("artifact-id")

# Load an artifact into memory
data = client.get_artifact_data("artifact-id")
```

### Stacks and Components

```python
# List all stacks
stacks = client.list_stacks()

# Get your active stack
active_stack = client.active_stack_model

# List all orchestrators
orchestrators = client.list_stack_components(
    component_type="orchestrator"
)
```

### Active User and Context

```python
# Get information about the currently authenticated user
current_user = client.active_user

# Check which stack is currently active
active_stack = client.active_stack_model.name
```

## Filtering and Sorting Results

Most list methods support filtering and sorting:

```python
# Find pipeline runs on a specific stack
runs_on_stack = client.list_pipeline_runs(
    stack_id="stack-id",
    sort_by="desc:start_time"
)

# Find artifacts produced by a specific user
user_artifacts = client.list_artifacts(
    user_id=client.active_user.id
)
```

## Pagination

All list methods return paginated results:

```python
# Get the first page with 20 results
first_page = client.list_pipeline_runs(size=20, page=1)

# Get the second page
second_page = client.list_pipeline_runs(size=20, page=2)

# Iterate through all results across pages
all_runs = []
page = 1
while True:
    runs_page = client.list_pipeline_runs(size=20, page=page)
    if not runs_page:
        break
    all_runs.extend(runs_page)
    page += 1
```

## Common Use Cases

### Retrieving Run Metadata

```python
# Get a pipeline run
run = client.get_pipeline_run("run-id")

# Access metadata
print(f"Run status: {run.status}")
print(f"Start time: {run.start_time}")
print(f"End time: {run.end_time}")
print(f"Duration: {run.end_time - run.start_time}")
```

### Working with Step Runs

```python
# Get all steps from a pipeline run
run = client.get_pipeline_run("run-id")
step_runs = run.steps

# Or get steps directly
step_runs = client.list_run_steps(pipeline_run_id="run-id")
```

### Accessing Artifacts Between Pipelines

```python
# Get artifacts from a previous run to use in a new pipeline
artifacts = client.list_artifacts(
    pipeline_run_id="previous-run-id"
)

# Use artifacts in a new pipeline
for artifact in artifacts:
    # Do something with each artifact
    artifact_data = client.get_artifact_data(artifact.id)
```

## Advanced Usage

### Working with Models

```python
# List all models
models = client.list_models()

# Get a specific model
model = client.get_model("model-name")

# List model versions
versions = client.list_model_versions(model_id=model.id)
```

### Creating Resources

```python
# Create a schedule for a pipeline
client.create_schedule(
    name="daily-training",
    pipeline_id="pipeline-id",
    cron_expression="0 0 * * *"
)
```

## REST API Alternative

For non-Python environments, you can interact with ZenML through its REST API:

```bash
# Example: List pipelines using curl
curl -X GET "https://your-zenml-server/api/v1/pipelines" \
     -H "accept: application/json" \
     -H "Authorization: Bearer YOUR_API_KEY"
```

Visit the `/docs/` page of your ZenML server for a complete API reference.

## Best Practices

- Reuse the client instance throughout your application
- Use filtering to limit the number of results returned
- Check the SDK documentation for the latest available methods
- For large datasets, process results in smaller batches using pagination

For more detailed information about specific resources and operations, refer to the [ZenML SDK Documentation](https://sdkdocs.zenml.io/). 