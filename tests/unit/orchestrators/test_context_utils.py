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
from zenml.enums import MetadataContextTypes, StackComponentType
from zenml.repository import Repository
from zenml.steps import step


def test_pipeline_storing_stack_in_the_metadata_store(
    clean_repo, one_step_pipeline
):
    """Tests that returning an object of a type that wasn't specified (either
    directly or as part of the `Output` tuple annotation) raises an error."""

    @step
    def some_step_1() -> int:
        return 3

    pipeline_ = one_step_pipeline(some_step_1())
    pipeline_.run()

    repo = Repository()

    stack = repo.get_stack(repo.active_stack_name)
    metadata_store = stack.metadata_store
    stack_contexts = metadata_store.store.get_contexts_by_type(
        MetadataContextTypes.STACK.value
    )

    assert len(stack_contexts) == 1

    assert stack_contexts[0].custom_properties[
        StackComponentType.ORCHESTRATOR.value
    ].string_value == stack.orchestrator.json(sort_keys=True)
    assert stack_contexts[0].custom_properties[
        StackComponentType.ARTIFACT_STORE.value
    ].string_value == stack.artifact_store.json(sort_keys=True)
    assert stack_contexts[0].custom_properties[
        StackComponentType.METADATA_STORE.value
    ].string_value == stack.metadata_store.json(sort_keys=True)
