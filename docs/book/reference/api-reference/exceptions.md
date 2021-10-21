Module zenml.exceptions
=======================
ZenML specific exception definitions

Classes
-------

`AlreadyExistsException(message: str = None, name: str = '', resource_type: str = '')`
:   Raises exception when the `name` already exist in the system but an
    action is trying to create a resource with the same name.

    ### Ancestors (in MRO)

    * builtins.Exception
    * builtins.BaseException

`ArtifactInterfaceError(*args, **kwargs)`
:   Raises exception when interacting with the Artifact interface
    in an unsupported way.

    ### Ancestors (in MRO)

    * builtins.Exception
    * builtins.BaseException

`DoesNotExistException(name: str = '', reason: str = '', message='{} does not exist! This might be due to: {}')`
:   Raises exception when the `name` does not exist in the system but an
    action is being done that requires it to be present.

    ### Ancestors (in MRO)

    * builtins.Exception
    * builtins.BaseException

`EmptyDatasourceException(message='This datasource has not been used in any pipelines, therefore the associated data has no versions. Please use this datasouce in any ZenML pipeline with `pipeline.add_datasource(datasource)`')`
:   Raises exception when a datasource data is accessed without running
    an associated pipeline.

    ### Ancestors (in MRO)

    * builtins.Exception
    * builtins.BaseException

`GitException(message: str = 'There is a problem with git resolution. Please make sure that all relevant files are committed.')`
:   Raises exception when a problem occurs in git resolution.

    ### Ancestors (in MRO)

    * builtins.Exception
    * builtins.BaseException

`InitializationException(message='ZenML config is none. Did you do `zenml init`?')`
:   Raises exception when a function is run before zenml initialization.

    ### Ancestors (in MRO)

    * builtins.Exception
    * builtins.BaseException

`PipelineInterfaceError(*args, **kwargs)`
:   Raises exception when interacting with the Pipeline interface
    in an unsupported way.

    ### Ancestors (in MRO)

    * builtins.Exception
    * builtins.BaseException

`PipelineNotSucceededException(name: str = '', message: str = '{} is not yet completed successfully.')`
:   Raises exception when trying to fetch artifacts from a not succeeded
    pipeline.

    ### Ancestors (in MRO)

    * builtins.Exception
    * builtins.BaseException

`StepInterfaceError(*args, **kwargs)`
:   Raises exception when interacting with the Step interface
    in an unsupported way.

    ### Ancestors (in MRO)

    * builtins.Exception
    * builtins.BaseException