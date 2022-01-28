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

import pytest

from zenml.exceptions import StepInterfaceError
from zenml.materializers import BuiltInMaterializer
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.steps import Output, step


def test_call_step_with_missing_materializer_for_type():
    """Tests that calling a step with an output without registered
    materializer raises a StepInterfaceError."""

    class MyTypeWithoutMaterializer:
        pass

    @step
    def some_step() -> MyTypeWithoutMaterializer:
        return MyTypeWithoutMaterializer()

    with pytest.raises(StepInterfaceError):
        some_step()()


def test_call_step_with_default_materializer_registered():
    """Tests that calling a step with a registered default materializer for the
    output works."""

    class MyType:
        pass

    class MyTypeMaterializer(BaseMaterializer):
        ASSOCIATED_TYPES = [MyType]

    @step
    def some_step() -> MyType:
        return MyType()

    with does_not_raise():
        some_step()()


def test_configure_step_with_wrong_materializer_class():
    """Tests that passing a random class as a materializer raises a
    StepInterfaceError."""

    @step
    def some_step() -> Output(some_output=int):
        pass

    with pytest.raises(StepInterfaceError):
        some_step().with_return_materializers(str)  # noqa


def test_configure_step_with_wrong_materializer_key():
    """Tests that passing a materializer for a non-existent argument raises a
    StepInterfaceError."""

    @step
    def some_step() -> Output(some_output=int):
        pass

    with pytest.raises(StepInterfaceError):
        materializers = {"some_nonexistent_output": BaseMaterializer}
        some_step().with_return_materializers(materializers)


def test_configure_step_with_wrong_materializer_class_in_dict():
    """Tests that passing a wrong class as materializer for a specific output
    raises a StepInterfaceError."""

    @step
    def some_step() -> Output(some_output=int):
        pass

    materializers = {"some_output": "not_a_materializer_class"}
    with pytest.raises(StepInterfaceError):
        some_step().with_return_materializers(materializers)  # noqa


def test_setting_a_materializer_for_a_step_with_multiple_outputs():
    """Tests that setting a materializer for a step with multiple outputs
    sets the materializer for all the outputs."""

    @step
    def some_step() -> Output(some_output=int, some_other_output=str):
        pass

    step_instance = some_step().with_return_materializers(BaseMaterializer)
    assert step_instance.get_materializers()["some_output"] is BaseMaterializer
    assert (
        step_instance.get_materializers()["some_other_output"]
        is BaseMaterializer
    )


def test_materializer_source_execution_parameter_changes_when_materializer_changes():
    """Tests that changing the step materializer changes the materializer
    source execution parameter."""

    @step
    def some_step() -> int:
        return 1

    class MyCustomMaterializer(BuiltInMaterializer):
        pass

    step_1 = some_step().with_return_materializers(BuiltInMaterializer)
    step_2 = some_step().with_return_materializers(MyCustomMaterializer)

    key = "zenml-output_materializer_source"
    assert (
        step_1._internal_execution_parameters[key]
        != step_2._internal_execution_parameters[key]
    )


def test_materializer_with_subclassing_parameter():
    """Tests whether the steps work where one parameter subclasses one of the
    registered types"""

    class MyFloatType(float):
        pass

    @step
    def some_step() -> MyFloatType:
        return MyFloatType(3.0)

    with does_not_raise():
        some_step()()


def test_materializer_with_parameter_with_more_than_one_baseclass():
    """Tests if the materializer selection work where the parameter has more
    than one baseclass, however only one of the types is registered"""

    class MyOtherType:
        pass

    class MyFloatType(float, MyOtherType):
        pass

    @step
    def some_step() -> MyFloatType:
        return MyFloatType(3.0)

    with does_not_raise():
        some_step()()


def test_materializer_with_parameter_with_more_than_one_conflicting_baseclass():
    """Tests the case where the output parameter is inheriting from more than
    one baseclass which have different default materializers"""

    class MyFirstType:
        pass

    class MySecondType:
        pass

    class MyFirstMaterializer(BaseMaterializer):
        ASSOCIATED_TYPES = [MyFirstType]

    class MySecondMaterializer(BaseMaterializer):
        ASSOCIATED_TYPES = [MySecondType]

    class MyConflictingType(MyFirstType, MySecondType):
        pass

    @step
    def some_step() -> MyConflictingType:
        return MyConflictingType()

    with pytest.raises(StepInterfaceError):
        some_step()()


def test_materializer_with_conflicting_parameter_and_explicit_materializer():
    """Tests the case where the output parameter is inheriting from more than
    one baseclass which have different default materializers but the
    materializer is explicitly defined"""

    class MyFirstType:
        pass

    class MySecondType:
        pass

    class MyFirstMaterializer(BaseMaterializer):
        ASSOCIATED_TYPES = [MyFirstType]

    class MySecondMaterializer(BaseMaterializer):
        ASSOCIATED_TYPES = [MySecondType]

    class MyConflictingType(MyFirstType, MySecondType):
        pass

    @step
    def some_step() -> MyConflictingType:
        return MyConflictingType()

    with does_not_raise():
        some_step().with_return_materializers(MyFirstMaterializer)()
