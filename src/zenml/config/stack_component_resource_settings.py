from typing import Set

from zenml.config.base_settings import BaseSettings


class StackComponentResourceSettings(BaseSettings):
    """Parent class for stack component resource settings.

    Orchestrators and step operators should subclass this class and define which
    config/setting attributes are related to infrastructure resources and can
    be defined using the `ResourceSettings`.
    """

    @classmethod
    def get_allowed_resource_settings_keys(cls) -> Set[str]:
        """Get a set of keys that can be defined using the resource settings.

        Returns:
            Set of keys that can be defined using the resource settings.
        """
        for class_ in cls.__mro__[1:]:
            if issubclass(class_, StackComponentResourceSettings):
                return set(class_.model_fields)
        else:
            return set()
