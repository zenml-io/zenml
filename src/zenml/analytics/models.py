#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Helper models for ZenML analytics."""
from typing import Any, ClassVar, Dict, List

from pydantic import BaseModel


class AnalyticsTrackedModelMixin(BaseModel):
    """Mixin for models that are tracked through analytics events.

    Classes that have information tracked in analytics events can inherit
    from this mixin and implement the abstract methods. The `@track_method`
    decorator will detect function arguments and return values that inherit
    from this class and will include the `ANALYTICS_FIELDS` attributes as
    tracking metadata.
    """

    ANALYTICS_FIELDS: ClassVar[List[str]] = []

    def get_analytics_metadata(self) -> Dict[str, Any]:
        """Get the analytics metadata for the model.

        Returns:
            Dict of analytics metadata.
        """
        metadata = {}
        for field_name in self.ANALYTICS_FIELDS:
            metadata[field_name] = getattr(self, field_name, None)
        return metadata
