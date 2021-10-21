Module zenml.core.utils
=======================

Functions
---------

    
`define_json_config_settings_source(config_dir: str, config_name: str) ‑> Callable`
:   Define a function to essentially deserialize a model from a serialized
    json config.
    
    Args:
        config_dir: A path to a dir where we want the config file to exist.
        config_name: Full name of config file.
    
    Returns:
        A `json_config_settings_source` callable reading from the passed path.

    
`generate_customise_sources(file_dir: str, file_name: str)`
:   Generate a customise_sources function as defined here:
    https://pydantic-docs.helpmanual.io/usage/settings/. This function
    generates a function that configures the priorities of the sources through
    which the model is loaded. The important thing to note here is that the
    `define_json_config_settings_source` is dynamically generates with the
    provided file_dir and file_name. This allows us to dynamically generate
    a file name for the serialization and deserialization of the model.
    
    Args:
        file_dir: Dir where file is stored.
        file_name: Name of the file to persist.
    
    Returns:
        A `customise_sources` class method to be defined the a Pydantic
        BaseSettings inner Config class.