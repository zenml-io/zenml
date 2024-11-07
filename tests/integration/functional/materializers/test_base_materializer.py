#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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

from zenml import pipeline, step
from zenml.materializers.base_materializer import BaseMaterializer

IMMEDIATE_CLEANUP_SAVE_DIR = None
IMMEDIATE_CLEANUP_LOAD_DIR = None
DELAYED_CLEANUP_SAVE_DIR = None
DELAYED_CLEANUP_LOAD_DIR = None


class CustomType:
    pass


class ImmediateCleanupMaterializer(BaseMaterializer):
    ASSOCIATED_TYPES = (CustomType,)

    def load(self, data_type):
        global IMMEDIATE_CLEANUP_LOAD_DIR
        with self.get_temporary_directory(delete_at_exit=True) as temp_dir:
            IMMEDIATE_CLEANUP_LOAD_DIR = temp_dir
            return CustomType()

    def save(self, data):
        global IMMEDIATE_CLEANUP_SAVE_DIR
        with self.get_temporary_directory(delete_at_exit=True) as temp_dir:
            IMMEDIATE_CLEANUP_SAVE_DIR = temp_dir


class DelayedCleanupMaterializer(BaseMaterializer):
    ASSOCIATED_TYPES = (CustomType,)

    def load(self, data_type):
        global DELAYED_CLEANUP_LOAD_DIR
        with self.get_temporary_directory(delete_at_exit=False) as temp_dir:
            DELAYED_CLEANUP_LOAD_DIR = temp_dir
            return CustomType()

    def save(self, data):
        global DELAYED_CLEANUP_SAVE_DIR
        with self.get_temporary_directory(delete_at_exit=False) as temp_dir:
            DELAYED_CLEANUP_SAVE_DIR = temp_dir


@step
def step_with_custom_type_output() -> CustomType:
    return CustomType()


@step
def verify_immediate_delete_step(input_: CustomType) -> None:
    assert not os.path.exists(IMMEDIATE_CLEANUP_SAVE_DIR)
    assert not os.path.exists(IMMEDIATE_CLEANUP_LOAD_DIR)


@step
def verify_delayed_delete_step(input_: CustomType) -> None:
    # The save from previous step does not exist anymore
    assert not os.path.exists(DELAYED_CLEANUP_SAVE_DIR)
    # The load directory exists during the step execution
    assert os.path.exists(DELAYED_CLEANUP_LOAD_DIR)


def test_immediate_temporary_directory_cleanup_inside_step(clean_client):
    global IMMEDIATE_CLEANUP_SAVE_DIR, IMMEDIATE_CLEANUP_LOAD_DIR
    IMMEDIATE_CLEANUP_SAVE_DIR = None
    IMMEDIATE_CLEANUP_LOAD_DIR = None

    @pipeline
    def test_pipeline():
        artifact = step_with_custom_type_output.with_options(
            output_materializers=ImmediateCleanupMaterializer
        )()
        verify_immediate_delete_step(artifact)

    test_pipeline()

    # Gets cleaned up after step execution
    assert not os.path.exists(IMMEDIATE_CLEANUP_SAVE_DIR)
    assert not os.path.exists(IMMEDIATE_CLEANUP_LOAD_DIR)


def test_delayed_temporary_directory_cleanup_inside_step(clean_client):
    global DELAYED_CLEANUP_LOAD_DIR, DELAYED_CLEANUP_SAVE_DIR
    DELAYED_CLEANUP_SAVE_DIR = None
    DELAYED_CLEANUP_LOAD_DIR = None

    @pipeline
    def test_pipeline():
        artifact = step_with_custom_type_output.with_options(
            output_materializers=DelayedCleanupMaterializer
        )()
        verify_delayed_delete_step(artifact)

    test_pipeline()

    # Gets cleaned up after step execution
    assert not os.path.exists(DELAYED_CLEANUP_LOAD_DIR)
    assert not os.path.exists(DELAYED_CLEANUP_SAVE_DIR)


def test_materializer_temporary_directory_cleanup_outside_step():
    global IMMEDIATE_CLEANUP_LOAD_DIR, DELAYED_CLEANUP_LOAD_DIR
    IMMEDIATE_CLEANUP_LOAD_DIR = None
    materializer = ImmediateCleanupMaterializer(uri=".")
    materializer.load(CustomType)
    # Gets cleaned up immediately
    assert not os.path.exists(IMMEDIATE_CLEANUP_LOAD_DIR)

    DELAYED_CLEANUP_LOAD_DIR = None
    materializer = DelayedCleanupMaterializer(uri=".")
    materializer.load(CustomType)
    # Does not get cleaned up because not running inside a step
    assert os.path.exists(DELAYED_CLEANUP_LOAD_DIR)
