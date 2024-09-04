from typing import Set

from zenml.config.base_settings import BaseSettings
from zenml.logger import get_logger

logger = get_logger(__name__)


class StackComponentResourceSettings(BaseSettings):
    """Parent class for stack component settings.

    This class allows stack component such as orchestrators and step operators
    to define which values from the `ResourceSettings` object they accept.
    """

    @classmethod
    def get_allowed_resource_settings_keys(cls) -> Set[str]:
        for class_ in cls.__mro__[1:]:
            if issubclass(class_, StackComponentResourceSettings):
                return set(class_.model_fields)
        else:
            return set()
