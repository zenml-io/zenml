from pathlib import Path
from typing import Any, Callable, Dict, Tuple, Type, cast

from pydantic import BaseSettings
from pydantic.env_settings import SettingsSourceCallable

from zenml.io import fileio
from zenml.logger import get_logger
from zenml.utils import yaml_utils

logger = get_logger(__name__)


def define_json_config_settings_source(
    config_dir: str, config_name: str
) -> SettingsSourceCallable:
    """
    Define a function to essentially deserialize a model from a serialized
    json config.

    Args:
        config_dir: A path to a dir where we want the config file to exist.
        config_name: Full name of config file.

    Returns:
        A `json_config_settings_source` callable reading from the passed path.
    """

    def json_config_settings_source(settings: BaseSettings) -> Dict[str, Any]:
        """
        A simple settings source that loads variables from a YAML file
        at the project's root.

        Here we happen to choose to use the `env_file_encoding` from Config
        when reading the config json file.

        Args:
            settings (BaseSettings): BaseSettings from pydantic.

        Returns:
            A dict with all configuration, empty dict if config not found.
        """
        full_path = Path(config_dir) / config_name
        logger.debug(f"Parsing file: {full_path}")
        if fileio.file_exists(str(full_path)):
            return cast(Dict[str, Any], yaml_utils.read_json(str(full_path)))
        return {}

    return json_config_settings_source


def generate_customise_sources(
    file_dir: str, file_name: str
) -> Callable[
    [
        Type[BaseSettings.Config],
        SettingsSourceCallable,
        SettingsSourceCallable,
        SettingsSourceCallable,
    ],
    Tuple[SettingsSourceCallable, ...],
]:
    """Generate a customise_sources function as defined here:
    https://pydantic-docs.helpmanual.io/usage/settings/. This function
    generates a function that configures the priorities of the sources through
    which the model is loaded. The important thing to note here is that the
    `define_json_config_settings_source` is dynamically generated with the
    provided file_dir and file_name. This allows us to dynamically generate
    a file name for the serialization and deserialization of the model.

    Args:
        file_dir: Dir where file is stored.
        file_name: Name of the file to persist.

    Returns:
        A `customise_sources` class method to be defined the a Pydantic
        BaseSettings inner Config class.
    """

    def customise_sources(
        cls: Type[BaseSettings.Config],
        init_settings: SettingsSourceCallable,
        env_settings: SettingsSourceCallable,
        file_secret_settings: SettingsSourceCallable,
    ) -> Tuple[SettingsSourceCallable, ...]:
        """Defines precedence of sources to read/write settings from."""
        return (
            init_settings,
            env_settings,
            define_json_config_settings_source(
                file_dir,
                file_name,
            ),
            file_secret_settings,
        )

    return classmethod(customise_sources)  # type: ignore[return-value]
