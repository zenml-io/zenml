from pathlib import Path
from typing import Dict, Any, Callable, Text

from pydantic import BaseSettings

from zenml.utils import path_utils, yaml_utils


def define_yaml_config_settings_source(
    config_dir: Text, config_name: Text
) -> Callable:
    """
    Define a function to read settings from a yaml config.

    Args:
        config_dir: A path to a dir where we want the config file to exist.
        config_name: Full name of config file.

    Returns:
        A `yaml_config_settings_source` callable reading from the passed path.
    """

    def yaml_config_settings_source(settings: BaseSettings) -> Dict[str, Any]:
        """
        A simple settings source that loads variables from a YAML file
        at the project's root.

        Here we happen to choose to use the `env_file_encoding` from Config
        when reading the config yaml file.

        Args:
            settings (BaseSettings): BaseSettings from pydantic.

        Returns:
            A dict with all configuration, empty dict if config not found.
        """
        full_path = Path(config_dir) / config_name
        if path_utils.file_exists(str(full_path)):
            return yaml_utils.read_yaml(str(full_path))
        return {}

    return yaml_config_settings_source
