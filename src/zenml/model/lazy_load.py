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
"""Model Version Data Lazy Loader definition."""

from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from zenml.models import ModelVersionResponse, PipelineRunResponse


class ModelVersionDataLazyLoader(BaseModel):
    """Model Version Data Lazy Loader helper class.

    It helps the inner codes to fetch proper artifact,
    model version metadata or artifact metadata from the
    model version during runtime time of the step.
    """

    model_name: str
    model_version: Optional[str] = None
    artifact_name: Optional[str] = None
    artifact_version: Optional[str] = None
    metadata_name: Optional[str] = None

    # TODO: In Pydantic v2, the `model_` is a protected namespaces for all
    #  fields defined under base models. If not handled, this raises a warning.
    #  It is possible to suppress this warning message with the following
    #  configuration, however the ultimate solution is to rename these fields.
    #  Even though they do not cause any problems right now, if we are not
    #  careful we might overwrite some fields protected by pydantic.
    model_config = ConfigDict(protected_namespaces=())

    def _get_model_response(
        self, pipeline_run: "PipelineRunResponse"
    ) -> "ModelVersionResponse":
        # if the version/number is None -> return the model in context
        if self.model_version is None:
            if mv := pipeline_run.model_version:
                if mv.model.name != self.model_name:
                    raise RuntimeError(
                        "Lazy loading of the model failed, since given name "
                        f"`{self.model_name}` does not match the model name "
                        f"in the pipeline context: `{mv.model.name}`."
                    )
                return mv
            else:
                raise RuntimeError(
                    "Lazy loading of the model failed, since the model version "
                    "is not set in the pipeline context."
                )

        # else return the model version by version
        else:
            from zenml.client import Client

            try:
                return Client().get_model_version(
                    model_name_or_id=self.model_name,
                    model_version_name_or_number_or_id=self.model_version,
                )
            except KeyError as e:
                raise RuntimeError(
                    "Lazy loading of the model version failed: "
                    f"no model `{self.model_name}` with version "
                    f"`{self.model_version}` could be found."
                ) from e
