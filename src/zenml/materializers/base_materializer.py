#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

from zenml.materializers.materializer_factory import MaterializerFactory


class BaseMaterializerMeta(type):
    def __new__(mcs, name, bases, dct):
        """ """

        cls = super().__new__(mcs, name, bases, dct)
        if name != "BaseMaterializer":
            assert cls.TYPE_NAME != "base", (
                f"You have used the name `base` as a TYPE_NAME "
                f"for your class {name}. When you are defining a new "
                f"materializer, please make sure that you give it a "
                f"TYPE_NAME other than `base`."
            )
            MaterializerFactory.register_type(cls.TYPE_NAME, cls)
        return cls


class BaseMaterializer(metaclass=BaseMaterializerMeta):
    """Base Materializer to realize artifact data."""

    TYPE_NAME = "base"

    def __init__(self, artifact):
        self.artifact = artifact
