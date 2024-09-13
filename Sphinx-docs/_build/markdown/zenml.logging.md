# zenml.logging package

## Submodules

## zenml.logging.step_logging module

ZenML logging handler.

### *class* zenml.logging.step_logging.StepLogsStorage(logs_uri: str, max_messages: int = 100, time_interval: int = 15, merge_files_interval: int = 600)

Bases: `object`

Helper class which buffers and stores logs to a given URI.

#### *property* artifact_store *: [BaseArtifactStore](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore)*

Returns the active artifact store.

Returns:
: The active artifact store.

#### merge_log_files(merge_all_files: bool = False) → None

Merges all log files into one in the given URI.

Called on the logging context exit.

Args:
: merge_all_files: whether to merge all files or only raw files

#### save_to_file(force: bool = False) → None

Method to save the buffer to the given URI.

Args:
: force: whether to force a save even if the write conditions not met.

#### write(text: str) → None

Main write method.

Args:
: text: the incoming string.

### *class* zenml.logging.step_logging.StepLogsStorageContext(logs_uri: str)

Bases: `object`

Context manager which patches stdout and stderr during step execution.

### zenml.logging.step_logging.fetch_logs(zen_store: [BaseZenStore](zenml.zen_stores.md#zenml.zen_stores.base_zen_store.BaseZenStore), artifact_store_id: str | UUID, logs_uri: str, offset: int = 0, length: int = 16777216) → str

Fetches the logs from the artifact store.

Args:
: zen_store: The store in which the artifact is stored.
  artifact_store_id: The ID of the artifact store.
  logs_uri: The URI of the artifact.
  offset: The offset from which to start reading.
  length: The amount of bytes that should be read.

Returns:
: The logs as a string.

Raises:
: DoesNotExistException: If the artifact does not exist in the artifact
  : store.

### zenml.logging.step_logging.prepare_logs_uri(artifact_store: [BaseArtifactStore](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore), step_name: str, log_key: str | None = None) → str

Generates and prepares a URI for the log file or folder for a step.

Args:
: artifact_store: The artifact store on which the artifact will be stored.
  step_name: Name of the step.
  log_key: The unique identification key of the log file.

Returns:
: The URI of the log storage (file or folder).

### zenml.logging.step_logging.remove_ansi_escape_codes(text: str) → str

Auxiliary function to remove ANSI escape codes from a given string.

Args:
: text: the input string

Returns:
: the version of the input string where the escape codes are removed.

## Module contents

Logging utilities.
