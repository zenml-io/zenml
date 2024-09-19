# zenml.integrations.databricks.utils package

## Submodules

## zenml.integrations.databricks.utils.databricks_utils module

Databricks utilities.

### zenml.integrations.databricks.utils.databricks_utils.convert_step_to_task(task_name: str, command: str, arguments: List[str], libraries: List[str] | None = None, depends_on: List[str] | None = None, zenml_project_wheel: str | None = None, job_cluster_key: str | None = None) → Task

Convert a ZenML step to a Databricks task.

Args:
: task_name: Name of the task.
  command: Command to run.
  arguments: Arguments to pass to the command.
  libraries: List of libraries to install.
  depends_on: List of tasks to depend on.
  zenml_project_wheel: Path to the ZenML project wheel.
  job_cluster_key: ID of the Databricks job_cluster_key.

Returns:
: Databricks task.

### zenml.integrations.databricks.utils.databricks_utils.sanitize_labels(labels: Dict[str, str]) → None

Update the label values to be valid Kubernetes labels.

See:
[https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/#syntax-and-character-set](https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/#syntax-and-character-set)

Args:
: labels: the labels to sanitize.

## Module contents

Utilities for Databricks integration.
