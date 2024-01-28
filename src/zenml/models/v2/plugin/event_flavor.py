from typing import Dict, Any

from zenml.plugins.base_plugin_flavor import BasePluginFlavorResponse


class EventFlavorResponse(BasePluginFlavorResponse):
    """Response model for Event Flavors."""

    source_config_schema: Dict[str, Any]
    filter_config_schema: Dict[str, Any]
