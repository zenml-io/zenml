from zenml.utils.enum_utils import StrEnum


class EventConfigurationType(StrEnum):
    """All possible types an event configuration types."""

    SOURCE = "SOURCE"
    FILTER = "FILTER"