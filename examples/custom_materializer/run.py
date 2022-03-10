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

import os
from typing import Type

from zenml.artifacts import DataArtifact
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.pipelines import pipeline
from zenml.steps import step


class MyObj:
    def __init__(self, name: str):
        self.name = name


class MyMaterializer(BaseMaterializer):
    ASSOCIATED_TYPES = (MyObj,)
    ASSOCIATED_ARTIFACT_TYPES = (DataArtifact,)

    def handle_input(self, data_type: Type[MyObj]) -> MyObj:
        """Read from artifact store"""
        super().handle_input(data_type)
        with fileio.open(os.path.join(self.artifact.uri, "data.txt"), "r") as f:
            name = f.read()
        return MyObj(name=name)

    def handle_return(self, my_obj: MyObj) -> None:
        """Write to artifact store"""
        super().handle_return(my_obj)
        with fileio.open(os.path.join(self.artifact.uri, "data.txt"), "w") as f:
            f.write(my_obj.name)


@step
def step1() -> MyObj:
    return MyObj("jk")


@step
def step2(my_obj: MyObj):
    print(my_obj.name)


@pipeline
def pipe(step1, step2):
    step2(step1())


if __name__ == "__main__":
    pipe(
        step1=step1().with_return_materializers(MyMaterializer), step2=step2()
    ).run()
