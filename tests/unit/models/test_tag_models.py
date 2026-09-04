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

from datetime import datetime
from uuid import uuid4

from zenml.enums import ColorVariants
from zenml.models import TagResponse, TagResponseBody, TagResponseMetadata


def test_tag_response_repr():
    """Test that a tag's repr is short and human-readable."""
    tag = TagResponse(
        id=uuid4(),
        name="my_tag",
        body=TagResponseBody(
            created=datetime.now(),
            updated=datetime.now(),
            color=ColorVariants.PURPLE,
            exclusive=False,
        ),
        metadata=TagResponseMetadata(tagged_count=0),
    )

    assert repr(tag) == "Tag(name=my_tag, color=purple)"
