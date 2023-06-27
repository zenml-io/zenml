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

from zenml.utils.singleton import SingletonMetaClass


class SingletonClass(metaclass=SingletonMetaClass):
    pass


def test_singleton_classes_only_create_one_instance():
    """Tests that a class with metaclass `SingletonMetaClass` only creates one instance."""
    assert SingletonClass() is SingletonClass()


def test_singleton_class_init_gets_called_once(mocker):
    """Tests that the singleton class __init__ method gets called only once when the instance is created."""
    mocker.patch.object(SingletonClass, "__init__", return_value=None)
    # make sure the instance doesn't exist
    SingletonClass._clear()

    SingletonClass()
    SingletonClass.__init__.assert_called_once()
    SingletonClass()
    SingletonClass.__init__.assert_called_once()


def test_singleton_instance_clearing():
    """Tests that the singleton instance can be cleared by calling `_clear()`."""
    instance = SingletonClass()

    SingletonClass._clear()

    assert instance is not SingletonClass()


def test_singleton_instance_exist():
    """Unit test for `SingletonMetaClass._exists()`."""
    SingletonClass()
    assert SingletonClass._exists()

    SingletonClass._clear()
    assert not SingletonClass._exists()

    SingletonClass()
    assert SingletonClass._exists()


def test_singleton_metaclass_can_be_used_for_multiple_classes():
    """Tests that multiple classes can use the `SingletonMetaClass` and their instances don't get mixed up."""

    class SecondSingletonClass(metaclass=SingletonMetaClass):
        pass

    assert SingletonClass() is not SecondSingletonClass()
    assert type(SingletonClass()) is SingletonClass
    assert type(SecondSingletonClass()) is SecondSingletonClass
