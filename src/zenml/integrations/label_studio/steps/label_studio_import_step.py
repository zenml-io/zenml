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
from typing import Optional

from zenml.artifacts.data_artifact import DataArtifact
from zenml.logger import get_logger
from zenml.steps import BaseStep, BaseStepConfig, StepContext

logger = get_logger(__name__)


class LabelStudioImportStepConfig(BaseStepConfig):
    """Step config definition for Label studio import step."""

    output_format: str


class LabelStudioImportStep(BaseStep):
    """Imports data in a format that Label Studio can understand."""

    def entrypoint(
        self,
        dataset_name: str,
        config: LabelStudioImportStepConfig,
        context: StepContext,
    ) -> Optional[DataArtifact]:
        """Main entrypoint function for the Label Studio export step."""
        annotator = context.stack.annotator
        if annotator and annotator._connection_available():
            return annotator.get_converted_dataset(
                dataset_name=dataset_name, output_format=config.output_format
            )
        else:
            logger.warning("No active annotator.")


# def label_studio_import_step(
#     output_format: str, enable_cache: Optional[bool] = None
# ) -> LabelStudioImportStep:
#     """Shortcut function to create a new instance of the import step.

#     Combines the config and the step classes to create a new instance of the
#     step.
#     """
#     # config = LabelStudioImportStepConfig(output_format=output_format)
#     # return LabelStudioImportStep(
#     #     dataset_name=dataset_name, config=config, context=StepContext
#     # )

#     # if enable_cache is None:
#     #     enable_cache = True

#     # step_type = type(
#     #     step_name,
#     #     (WhylogsProfilerStep,),
#     #     {
#     #         INSTANCE_CONFIGURATION: {
#     #             PARAM_ENABLE_CACHE: enable_cache,
#     #             PARAM_CREATED_BY_FUNCTIONAL_API: True,
#     #         },
#     #     },
#     # )

#     # return cast(
#     #     WhylogsProfilerStep,
#     #     step_type(
#     #         WhylogsProfilerConfig(
#     #             dataset_name=dataset_name,
#     #             dataset_timestamp=dataset_timestamp,
#     #             tags=tags,
#     #         )
#     #     ),
#     # )
