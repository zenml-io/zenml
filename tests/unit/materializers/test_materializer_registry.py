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
from contextlib import ExitStack as does_not_raise

from zenml.materializers.base_materializer import BaseMaterializer
from zenml.steps import step


def test_materializer_with_subclassing_parameter():
    """Tests whether the steps work where one parameter subclasses one of the
    registered types."""

    class MyFloatType(float):
        pass

    @step
    def some_step() -> MyFloatType:
        return MyFloatType(3.0)

    with does_not_raise():
        some_step()


def test_materializer_with_parameter_with_more_than_one_baseclass():
    """Tests if the materializer selection work where the parameter has more
    than one baseclass, however only one of the types is registered."""

    class MyOtherType:
        pass

    class MyFloatType(float, MyOtherType):
        pass

    @step
    def some_step() -> MyFloatType:
        return MyFloatType(3.0)

    with does_not_raise():
        some_step()


class MyFirstType:
    pass


class MySecondType:
    pass


class MyFirstMaterializer(BaseMaterializer):
    ASSOCIATED_TYPES = (MyFirstType,)


class MySecondMaterializer(BaseMaterializer):
    ASSOCIATED_TYPES = (MySecondType,)


class MyConflictingType(MyFirstType, MySecondType):
    pass


def test_materializer_with_parameter_with_more_than_one_conflicting_baseclass():
    """Tests the case where the output parameter is inheriting from more than
    one baseclass which have different default materializers."""

    @step
    def some_step() -> MyConflictingType:
        return MyConflictingType()

    with does_not_raise():
        some_step._finalize_configuration(
            input_artifacts={},
            external_artifacts={},
            model_artifacts_or_metadata={},
            client_lazy_loaders={},
        )

    # The step uses the materializer registered for the earliest class in the
    # python MRO
    assert (
        some_step.configuration.outputs["output"]
        .materializer_source[0]
        .attribute
        == "MyFirstMaterializer"
    )


def test_materializer_with_conflicting_parameter_and_explicit_materializer():
    """Tests the case where the output parameter is inheriting from more than
    one baseclass which have different default materializers but the
    materializer is explicitly defined."""

    @step
    def some_step() -> MyConflictingType:
        return MyConflictingType()

    with does_not_raise():
        some_step.configure(output_materializers=MyFirstMaterializer)()
