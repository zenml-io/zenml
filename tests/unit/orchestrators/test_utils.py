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

import pytest

from zenml.orchestrators.utils import get_cache_status


def test_get_cache_status_raises_no_error_when_none_passed():
    """Ensure get_cache_status raises no error when None is passed."""
    try:
        get_cache_status(None)
    except AttributeError:
        pytest.fail("`get_cache_status()` raised an `AttributeError`")


# def test_get_cache_status_works_when_running_pipeline_twice(clean_repo):
#     """Check that steps are cached when a pipeline is run twice successively."""
#     from zenml.pipelines import pipeline
#     from zenml.steps import step
#     from tfx.orchestration.portable.data_types import ExecutionInfo

#     @step
#     def step_one(enable_cache=True):
#         return 1

#     @pipeline
#     def some_pipeline(
#         step_one,
#     ):
#         step_one()

#     pipeline = some_pipeline(
#         step_one=step_one(),
#     )

#     pipeline.run()
#     pipeline.run()

#     first_run_execution_object = ExecutionInfo()
#     second_run_execution_object = ExecutionInfo()

#     assert get_cache_status(first_run_execution_object) is False
#     assert get_cache_status(second_run_execution_object) is True
#     assert get_cache_status(first_run_execution_object) != get_cache_status(
#         second_run_execution_object
#     )


"""

execution_id: Optional[int] = None
# The input map to feed to execution
input_dict: Dict[str, List[types.Artifact]] = attr.Factory(dict)
# The output map to feed to execution
output_dict: Dict[str, List[types.Artifact]] = attr.Factory(dict)
# The exec_properties to feed to execution
exec_properties: Dict[str, Any] = attr.Factory(dict)
# The uri to execution result, note that the drivers or executors and
# Launchers may not run in the same process, so they should use this uri to
# "return" execution result to the launcher.
execution_output_uri: Optional[str] = None
# Stateful working dir will be deterministic given pipeline, node and run_id.
# The typical usecase is to restore long running executor's state after
# eviction. For examples, a Trainer can use this directory to store
# checkpoints. This dir is undefined when Launcher.launch() is done.
stateful_working_dir: Optional[str] = None
# A temporary dir for executions and it is expected to be cleared up at the end
# of executions in both success and failure cases. This dir is undefined when
# Launcher.launch() is done.
tmp_dir: Optional[str] = None
# The config of this Node.
pipeline_node: Optional[pipeline_pb2.PipelineNode] = None
# The config of the pipeline that this node is running in.
pipeline_info: Optional[pipeline_pb2.PipelineInfo] = None
# The id of the pipeline run that this execution is in.
pipeline_run_id: Optional[str] = None
# LINT.ThenChange(../../proto/orchestration/execution_invocation.proto)

- Run the same pipeline (with cache enabled) twice inside a clean_repo
- Create an execution_info object with the right pipeline/run/step names
- Check if it returns False for the first run and True for the second one
"""
