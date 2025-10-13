#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Abstract base class for entrypoint configurations that run a pipeline."""

from zenml.entrypoints.base_entrypoint_configuration import (
    BaseEntrypointConfiguration,
)
from zenml.integrations.registry import integration_registry
from zenml.utils import source_utils


class DynamicPipelineEntrypointConfiguration(BaseEntrypointConfiguration):
    """Base class for entrypoint configurations that run an entire pipeline."""

    def run(self) -> None:
        """Prepares the environment and runs the configured pipeline."""
        snapshot = self.load_snapshot()

        # Activate all the integrations. This makes sure that all materializers
        # and stack component flavors are registered.
        integration_registry.activate_integrations()

        self.download_code_if_necessary(snapshot=snapshot)

        from zenml.pipelines.dynamic_pipeline_runtime import (
            initialize_runtime,
        )

        pipeline = source_utils.load(snapshot.pipeline_spec.source)
        initialize_runtime(pipeline=pipeline, snapshot=snapshot)

        pipeline(**snapshot.pipeline_spec.parameters)
