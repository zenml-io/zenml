# Copyright 2019 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
The implementation of the set of GenericType and GenericMeta class below is
inspired by the implementation by the Tensorflow Extended team, which can be
found here:

https://github.com/tensorflow/tfx/blob/master/tfx/dsl/component/experimental/annotations.py

The list of changes to improve the interaction with ZenML:

- The main classes are merged into a single class which serves as the base
class to be extended
- A class variable is added to be utilized while checking the type of T
- A few more classes are created on top of artifacts and primitives in order to
use the same paradigm with steps and datasources as well

"""
import inspect
from typing import Type

from six import with_metaclass


class GenericMeta(type):
    """ """

    def __getitem__(cls: Type["BaseAnnotation"], params):
        return cls._generic_getitem(params)


class BaseAnnotation(with_metaclass(GenericMeta, object)):
    """A main generic class which will be used as the base for annotations"""

    VALID_TYPES = None

    def __init__(self, object_type, _init_via_getitem=False):

        if not _init_via_getitem:
            class_name = self.__class__.__name__
            raise ValueError(
                f"{class_name} should be instantiated via %s[T], "
                f"where T is one of {self.VALID_TYPES}"
            )
        self.type = object_type

    def __repr__(self):
        return "%s[%s]" % (self.__class__.__name__, self.type)

    @classmethod
    def _generic_getitem(cls, params):
        """

        Args:
          params:

        Returns:

        """
        if inspect.isclass(params) and any(
            issubclass(params, t) for t in cls.VALID_TYPES
        ):
            return cls(params, _init_via_getitem=True)
        else:
            class_name = cls.__name__
            raise ValueError(
                f"Generic type `{class_name}[T]` expects the "
                f"single parameter T to be one of "
                f"{cls.VALID_TYPES}."
            )
