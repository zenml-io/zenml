# zenml.entrypoints package

## Submodules

## zenml.entrypoints.base_entrypoint_configuration module

Abstract base class for entrypoint configurations.

### *class* zenml.entrypoints.base_entrypoint_configuration.BaseEntrypointConfiguration(arguments: List[str])

Bases: `ABC`

Abstract base class for entrypoint configurations.

An entrypoint configuration specifies the arguments that should be passed
to the entrypoint and what is running inside the entrypoint.

Attributes:
: entrypoint_args: The parsed arguments passed to the entrypoint.

#### download_code_from_code_repository(code_reference: [CodeReferenceResponse](zenml.models.md#zenml.models.CodeReferenceResponse)) → None

Download code from a code repository.

Args:
: code_reference: The reference to the code.

#### download_code_if_necessary(deployment: [PipelineDeploymentResponse](zenml.models.md#zenml.models.PipelineDeploymentResponse), step_name: str | None = None) → None

Downloads user code if necessary.

Args:
: deployment: The deployment for which to download the code.
  step_name: Name of the step to be run. This will be used to
  <br/>
  > determine whether code download is necessary. If not given,
  > the DockerSettings of the pipeline will be used to make that
  > decision instead.

Raises:
: RuntimeError: If the current environment requires code download
  : but the deployment does not have a reference to any code.

#### *classmethod* get_entrypoint_arguments(\*\*kwargs: Any) → List[str]

Gets all arguments that the entrypoint command should be called with.

The argument list should be something that
argparse.ArgumentParser.parse_args(…) can handle (e.g.
[”–some_option”, “some_value”] or [”–some_option=some_value”]).
It needs to provide values for all options returned by the
get_entrypoint_options() method of this class.

Args:
: ```
  **
  ```
  <br/>
  kwargs: Keyword args.

Returns:
: A list of strings with the arguments.

Raises:
: ValueError: If no valid deployment ID is passed.

#### *classmethod* get_entrypoint_command() → List[str]

Returns a command that runs the entrypoint module.

This entrypoint module is responsible for running the entrypoint
configuration when called. Defaults to running the
zenml.entrypoints.entrypoint module.

**Note**: This command won’t work on its own but needs to be called with
: the arguments returned by the get_entrypoint_arguments(…)
  method of this class.

Returns:
: A list of strings with the command.

#### *classmethod* get_entrypoint_options() → Set[str]

Gets all options required for running with this configuration.

Returns:
: A set of strings with all required options.

#### load_deployment() → [PipelineDeploymentResponse](zenml.models.md#zenml.models.PipelineDeploymentResponse)

Loads the deployment.

Returns:
: The deployment.

#### *abstract* run() → None

Runs the entrypoint configuration.

## zenml.entrypoints.entrypoint module

Functionality to run ZenML steps or pipelines.

### zenml.entrypoints.entrypoint.main() → None

Runs the entrypoint configuration given by the command line arguments.

## zenml.entrypoints.pipeline_entrypoint_configuration module

Abstract base class for entrypoint configurations that run a pipeline.

### *class* zenml.entrypoints.pipeline_entrypoint_configuration.PipelineEntrypointConfiguration(arguments: List[str])

Bases: [`BaseEntrypointConfiguration`](#zenml.entrypoints.base_entrypoint_configuration.BaseEntrypointConfiguration)

Base class for entrypoint configurations that run an entire pipeline.

#### run() → None

Prepares the environment and runs the configured pipeline.

## zenml.entrypoints.step_entrypoint_configuration module

Base class for entrypoint configurations that run a single step.

### *class* zenml.entrypoints.step_entrypoint_configuration.StepEntrypointConfiguration(arguments: List[str])

Bases: [`BaseEntrypointConfiguration`](#zenml.entrypoints.base_entrypoint_configuration.BaseEntrypointConfiguration)

Base class for entrypoint configurations that run a single step.

If an orchestrator needs to run steps in a separate process or environment
(e.g. a docker container), this class can either be used directly or
subclassed if custom behavior is necessary.

### How to subclass:

Passing additional arguments to the entrypoint:
: If you need to pass additional arguments to the entrypoint, there are
  two methods that you need to implement:
  <br/>
  > * get_entrypoint_options(): This method should return all
  >   : the options that are required in the entrypoint. Make sure to
  >     include the result from the superclass method so the options
  >     are complete.
  > * get_entrypoint_arguments(…): This method should return
  >   : a list of arguments that should be passed to the entrypoint.
  >     Make sure to include the result from the superclass method so
  >     the arguments are complete.
  <br/>
  You’ll be able to access the argument values from self.entrypoint_args
  inside your StepEntrypointConfiguration subclass.

### How to use:

After you created your StepEntrypointConfiguration subclass, you only
have to run the entrypoint somewhere. To do this, you should execute the
command returned by the get_entrypoint_command() method with the
arguments returned by the get_entrypoint_arguments(…) method.

Example:

```
``
```

```
`
```

python
class MyStepEntrypointConfiguration(StepEntrypointConfiguration):

> …

class MyOrchestrator(BaseOrchestrator):
: def prepare_or_run_pipeline(
  : self,
    deployment: “PipelineDeployment”,
    stack: “Stack”,
  <br/>
  ) -> Any:
  : …
    <br/>
    cmd = MyStepEntrypointConfiguration.get_entrypoint_command()
    for step_name, step in pipeline.steps.items():
    <br/>
    > …
    <br/>
    > args = MyStepEntrypointConfiguration.get_entrypoint_arguments(
    > : step_name=step_name
    <br/>
    > )
    > # Run the command and pass it the arguments. Our example
    > # orchestrator here executes the entrypoint in a separate
    > # process, but in a real-world scenario you would probably run
    > # it inside a docker container or a different environment.
    > import subprocess
    > subprocess.check_call(cmd + args)

```
``
```

```
`
```

#### *classmethod* get_entrypoint_arguments(\*\*kwargs: Any) → List[str]

Gets all arguments that the entrypoint command should be called with.

The argument list should be something that
argparse.ArgumentParser.parse_args(…) can handle (e.g.
[”–some_option”, “some_value”] or [”–some_option=some_value”]).
It needs to provide values for all options returned by the
get_entrypoint_options() method of this class.

Args:
: ```
  **
  ```
  <br/>
  kwargs: Kwargs, must include the step name.

Returns:
: The superclass arguments as well as arguments for the name of the
  step to run.

#### *classmethod* get_entrypoint_options() → Set[str]

Gets all options required for running with this configuration.

Returns:
: The superclass options as well as an option for the name of the
  step to run.

#### post_run(pipeline_name: str, step_name: str) → None

Does cleanup or post-processing after the step finished running.

Subclasses should overwrite this method if they need to run any
additional code after the step execution.

Args:
: pipeline_name: Name of the parent pipeline of the step that was
  : executed.
  <br/>
  step_name: Name of the step that was executed.

#### run() → None

Prepares the environment and runs the configured step.

## Module contents

Initializations for ZenML entrypoints module.

### *class* zenml.entrypoints.PipelineEntrypointConfiguration(arguments: List[str])

Bases: [`BaseEntrypointConfiguration`](#zenml.entrypoints.base_entrypoint_configuration.BaseEntrypointConfiguration)

Base class for entrypoint configurations that run an entire pipeline.

#### run() → None

Prepares the environment and runs the configured pipeline.

### *class* zenml.entrypoints.StepEntrypointConfiguration(arguments: List[str])

Bases: [`BaseEntrypointConfiguration`](#zenml.entrypoints.base_entrypoint_configuration.BaseEntrypointConfiguration)

Base class for entrypoint configurations that run a single step.

If an orchestrator needs to run steps in a separate process or environment
(e.g. a docker container), this class can either be used directly or
subclassed if custom behavior is necessary.

### How to subclass:

Passing additional arguments to the entrypoint:
: If you need to pass additional arguments to the entrypoint, there are
  two methods that you need to implement:
  <br/>
  > * get_entrypoint_options(): This method should return all
  >   : the options that are required in the entrypoint. Make sure to
  >     include the result from the superclass method so the options
  >     are complete.
  > * get_entrypoint_arguments(…): This method should return
  >   : a list of arguments that should be passed to the entrypoint.
  >     Make sure to include the result from the superclass method so
  >     the arguments are complete.
  <br/>
  You’ll be able to access the argument values from self.entrypoint_args
  inside your StepEntrypointConfiguration subclass.

### How to use:

After you created your StepEntrypointConfiguration subclass, you only
have to run the entrypoint somewhere. To do this, you should execute the
command returned by the get_entrypoint_command() method with the
arguments returned by the get_entrypoint_arguments(…) method.

Example:

```
``
```

```
`
```

python
class MyStepEntrypointConfiguration(StepEntrypointConfiguration):

> …

class MyOrchestrator(BaseOrchestrator):
: def prepare_or_run_pipeline(
  : self,
    deployment: “PipelineDeployment”,
    stack: “Stack”,
  <br/>
  ) -> Any:
  : …
    <br/>
    cmd = MyStepEntrypointConfiguration.get_entrypoint_command()
    for step_name, step in pipeline.steps.items():
    <br/>
    > …
    <br/>
    > args = MyStepEntrypointConfiguration.get_entrypoint_arguments(
    > : step_name=step_name
    <br/>
    > )
    > # Run the command and pass it the arguments. Our example
    > # orchestrator here executes the entrypoint in a separate
    > # process, but in a real-world scenario you would probably run
    > # it inside a docker container or a different environment.
    > import subprocess
    > subprocess.check_call(cmd + args)

```
``
```

```
`
```

#### *classmethod* get_entrypoint_arguments(\*\*kwargs: Any) → List[str]

Gets all arguments that the entrypoint command should be called with.

The argument list should be something that
argparse.ArgumentParser.parse_args(…) can handle (e.g.
[”–some_option”, “some_value”] or [”–some_option=some_value”]).
It needs to provide values for all options returned by the
get_entrypoint_options() method of this class.

Args:
: ```
  **
  ```
  <br/>
  kwargs: Kwargs, must include the step name.

Returns:
: The superclass arguments as well as arguments for the name of the
  step to run.

#### *classmethod* get_entrypoint_options() → Set[str]

Gets all options required for running with this configuration.

Returns:
: The superclass options as well as an option for the name of the
  step to run.

#### post_run(pipeline_name: str, step_name: str) → None

Does cleanup or post-processing after the step finished running.

Subclasses should overwrite this method if they need to run any
additional code after the step execution.

Args:
: pipeline_name: Name of the parent pipeline of the step that was
  : executed.
  <br/>
  step_name: Name of the step that was executed.

#### run() → None

Prepares the environment and runs the configured step.
