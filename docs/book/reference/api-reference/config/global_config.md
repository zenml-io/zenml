Module zenml.config.global_config
=================================
Global config for the ZenML installation.

Classes
-------

`GlobalConfig(**data: Any)`
:   Class definition for the global config.
    
    Defines global data such as unique user ID and whether they opted in
    for analytics.
    
    We persist the attributes in the config file. For the global
    config, we want to persist the data as soon as it is initialized for
    the first time.

    ### Ancestors (in MRO)

    * zenml.core.base_component.BaseComponent
    * pydantic.env_settings.BaseSettings
    * pydantic.main.BaseModel
    * pydantic.utils.Representation

    ### Class variables

    `analytics_opt_in: bool`
    :

    `repo_active_stacks: Optional[Dict[str, str]]`
    :

    `user_id: uuid.UUID`
    :

    ### Methods

    `get_serialization_dir(self) ‑> str`
    :   Gets the global config dir for installed package.

    `get_serialization_file_name(self) ‑> str`
    :   Gets the global config dir for installed package.

    `set_stack_for_repo(self, repo_path: str, stack_key: str)`
    :   Sets the active stack for a specific repository.