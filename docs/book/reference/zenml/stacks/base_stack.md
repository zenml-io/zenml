Module zenml.stacks.base_stack
==============================

Classes
-------

`BaseStack(**values: Any)`
:   Base stack for ZenML.
    
    A ZenML stack brings together an Metadata Store, an Artifact Store, and
    an Orchestrator, the trifecta of the environment required to run a ZenML
    pipeline. A ZenML stack also happens to be a pydantic `BaseSettings`
    class, which means that there are multiple ways to use it.
    
    * You can set it via env variables.
    * You can set it through the config yaml file.
    * You can set it in code by initializing an object of this class, and
    passing it to pipelines as a configuration.
    
    In the case where a value is specified for the same Settings field in
    multiple ways, the selected value is determined as follows (in descending
    order of priority):
    
    * Arguments passed to the Settings class initializer.
    * Environment variables, e.g. zenml_var as described above.
    * Variables loaded from a config yaml file.
    * The default field values.

    ### Ancestors (in MRO)

    * pydantic.env_settings.BaseSettings
    * pydantic.main.BaseModel
    * pydantic.utils.Representation

    ### Class variables

    `Config`
    :   Configuration of settings.

    `artifact_store_name: str`
    :

    `metadata_store_name: str`
    :

    `orchestrator_name: str`
    :

    `stack_type: zenml.enums.StackTypes`
    :

    ### Instance variables

    `artifact_store: zenml.artifact_stores.base_artifact_store.BaseArtifactStore`
    :   Returns the artifact store of this stack.

    `metadata_store: zenml.metadata.base_metadata_store.BaseMetadataStore`
    :   Returns the metadata store of this stack.

    `orchestrator: zenml.orchestrators.base_orchestrator.BaseOrchestrator`
    :   Returns the orchestrator of this stack.