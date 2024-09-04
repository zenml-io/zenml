from typing import ClassVar, List

from zenml.config.base_settings import BaseSettings
from zenml.logger import get_logger

logger = get_logger(__name__)


class StackComponentSettings(BaseSettings):
    """Parent class for stack component settings.

    This class allows stack component such as orchestrators and step operators
    to define which values from the `ResourceSettings` object they accept.
    """

    ALLOWED_RESOURCE_SETTINGS_KEYS: ClassVar[List[str]] = []
