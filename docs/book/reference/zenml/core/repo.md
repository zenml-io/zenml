Module zenml.core.repo
======================
Base ZenML repository

Classes
-------

`Repository(path: str = None)`
:   ZenML repository definition.
    
    Every ZenML project exists inside a ZenML repository.
    
    Construct reference a ZenML repository.
    
    Args:
        path (str): Path to root of repository

    ### Static methods

    `init_repo(repo_path: str = '/home/hamza/workspace/maiot/github_temp/zenml', stack: zenml.stacks.base_stack.BaseStack = None, analytics_opt_in: bool = None)`
    :   Initializes a git repo with zenml.
        
        Args:
            repo_path (str): path to root of a git repo
            stack: Initial stack.
            analytics_opt_in: opt-in flag for analytics code.
        
        Raises:
            InvalidGitRepositoryError: If repository is not a git repository.
            NoSuchPathError: If the repo_path does not exist.

    ### Methods

    `clean(self)`
    :   Deletes associated metadata store, pipelines dir and artifacts

    `get_active_stack(self) ‑> zenml.stacks.base_stack.BaseStack`
    :   Get the active stack from global config.
        
        Returns:
            Currently active stack.

    `get_active_stack_key(*args, **kwargs)`
    :   Inner decorator function.

    `get_git_wrapper(self) ‑> zenml.core.git_wrapper.GitWrapper`
    :   Returns the git wrapper for the repo.

    `get_pipeline(self, pipeline_name: str, stack_key: Optional[str] = None) ‑> Optional[zenml.post_execution.pipeline.PipelineView]`
    :   Returns a pipeline for the given name or `None` if it doesn't exist.
        
        Args:
            pipeline_name: Name of the pipeline.
            stack_key: If specified, pipelines in the metadata store of the
                given stack are returned. Otherwise pipelines in the metadata
                store of the currently active stack are returned.

    `get_pipelines(*args, **kwargs)`
    :   Inner decorator function.

    `get_service(self) ‑> zenml.core.local_service.LocalService`
    :   Returns the active service. For now, always local.

    `set_active_stack(*args, **kwargs)`
    :   Inner decorator function.