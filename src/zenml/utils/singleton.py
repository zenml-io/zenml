#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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

from typing import Any, Optional, cast


class SingletonMetaClass(type):
    """Singleton metaclass.

    Use this metaclass to make any class into singleton:

    .. highlight:: python
    .. code-block:: python

        class OneRing(metaclass=SingletonMetaClass):
            def __init__(self, owner):
                self._owner = owner

            @property
            def owner(self):
                return self._owner

        the_one_ring = OneRing('Sauron')
        the_lost_ring = OneRing('Frodo')
        print(the_lost_ring.owner)  # Sauron
        OneRing._clear() # ring destroyed

    """

    __single_instance: Optional["SingletonMetaClass"] = None

    def __call__(cls, *args: Any, **kwargs: Any) -> "SingletonMetaClass":
        """Create or return the singleton instance."""

        if cls.__single_instance:
            return cls.__single_instance
        single_obj = super().__call__(*args, **kwargs)
        cls.__single_instance = single_obj
        single_obj.__init__(*args, **kwargs)
        return cast("SingletonMetaClass", single_obj)

    def _clear(cls) -> None:
        """Clear the singleton instance."""

        try:
            cls.__single_instance = None
        except KeyError:
            pass
