#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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

from typing import Any, Iterator, NamedTuple, Tuple, Type


class Output(object):
    """A named tuple with a default name that cannot be overridden."""

    def __init__(self, **kwargs: Type[Any]):
        # TODO [ENG-161]: do we even need the named tuple here or is
        #  a list of tuples (name, Type) sufficient?
        self.outputs = NamedTuple("ZenOutput", **kwargs)  # type: ignore[misc]

    def items(self) -> Iterator[Tuple[str, Type[Any]]]:
        """Yields a tuple of type (output_name, output_type)."""
        yield from self.outputs.__annotations__.items()
