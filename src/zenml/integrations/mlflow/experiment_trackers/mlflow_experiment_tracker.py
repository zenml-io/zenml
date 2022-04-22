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
from typing import Any, ClassVar, Dict, Optional

from mlflow import (  # type: ignore[import]
    ActiveRun,
    get_experiment_by_name,
    search_runs,
    set_experiment,
    set_tracking_uri,
    start_run,
)
from mlflow.entities import Experiment  # type: ignore[import]
from mlflow.store.db.db_types import DATABASE_ENGINES  # type: ignore[import]
from pydantic import root_validator, validator

from zenml.artifact_stores import LocalArtifactStore
from zenml.experiment_trackers.base_experiment_tracker import (
    BaseExperimentTracker,
)
from zenml.integrations.constants import MLFLOW
from zenml.logger import get_logger
from zenml.repository import Repository
from zenml.stack import StackValidator
from zenml.stack.stack_component_class_registry import (
    register_stack_component_class,
)

logger = get_logger(__name__)

MLFLOW_TRACKING_USERNAME = "MLFLOW_TRACKING_USERNAME"
MLFLOW_TRACKING_PASSWORD = "MLFLOW_TRACKING_PASSWORD"
MLFLOW_TRACKING_TOKEN = "MLFLOW_TRACKING_TOKEN"
MLFLOW_TRACKING_INSECURE_TLS = "MLFLOW_TRACKING_INSECURE_TLS"


@register_stack_component_class
class MLFlowExperimentTracker(BaseExperimentTracker):
    """Stores Mlflow configuration options.

    ZenML should take care of configuring MLflow for you, but should you still
    need access to the configuration inside your step:
    ```python
    from zenml.steps import StepContext

    @enable_mlflow
    @step
    def my_step(context: StepContext, ...)
        context.stack.experiment_tracker  # get the tracking_uri etc. from here
    ```
    """

    tracking_uri: Optional[str] = None
    tracking_username: Optional[str] = None
    tracking_password: Optional[str] = None
    tracking_token: Optional[str] = None
    tracking_insecure_tls: bool = False

    # Class Configuration
    FLAVOR: ClassVar[str] = MLFLOW

    @validator("tracking_uri")
    def _ensure_valid_tracking_uri(
        cls, tracking_uri: Optional[str] = None
    ) -> Optional[str]:
        """Ensures that the tracking uri is a valid mlflow tracking uri."""
        if tracking_uri:
            valid_schemes = DATABASE_ENGINES + ["http", "https", "file"]
            if not any(
                tracking_uri.startswith(scheme) for scheme in valid_schemes
            ):
                raise ValueError(
                    f"MLflow tracking uri does not start with one of the valid "
                    f"schemes {valid_schemes}. See "
                    f"https://www.mlflow.org/docs/latest/tracking.html#where-runs-are-recorded "
                    f"for more information."
                )
        return tracking_uri

    @root_validator
    def _ensure_authentication_if_necessary(
        cls, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Ensures that credentials or a token for authentication exist when
        running mlflow tracking with a remote backend."""
        tracking_uri = values.get("tracking_uri")

        if tracking_uri and cls.is_remote_tracking_uri(tracking_uri):
            # we need either username + password or a token to authenticate to
            # the remote backend
            basic_auth = values.get("tracking_username") and values.get(
                "tracking_password"
            )
            token_auth = values.get("tracking_token")

            if not (basic_auth or token_auth):
                raise ValueError(
                    f"MLflow experiment tracking with a remote backend "
                    f"{tracking_uri} is only when specifying either username "
                    f"and password or a authentication token in your stack "
                    f"component. To update your component, run the following "
                    f"command: `zenml experiment-tracker update "
                    f"{values['name']} --tracking_username=MY_USERNAME "
                    f"--tracking_password=MY_PASSWORD "
                    f"--tracking_token=MY_TOKEN` and specify either your "
                    f"username and password or token."
                )

        return values

    @staticmethod
    def is_remote_tracking_uri(tracking_uri: str) -> bool:
        return any(
            tracking_uri.startswith(prefix)
            for prefix in ["http://", "https://"]
        )

    @staticmethod
    def _local_mlflow_backend() -> str:
        """Returns the local mlflow backend inside the zenml artifact
        repository directory

        Returns:
            The MLflow tracking URI for the local mlflow backend.
        """
        repo = Repository(skip_repository_check=True)  # type: ignore[call-arg]
        artifact_store = repo.active_stack.artifact_store
        local_mlflow_backend_uri = os.path.join(artifact_store.path, "mlruns")
        if not os.path.exists(local_mlflow_backend_uri):
            os.makedirs(local_mlflow_backend_uri)
        return "file:" + local_mlflow_backend_uri

    def get_tracking_uri(self) -> str:
        """Returns the configured tracking URI or a local fallback."""
        return self.tracking_uri or self._local_mlflow_backend()

    def prepare_pipeline_run(self) -> None:
        """Prepares running the pipeline."""
        set_tracking_uri(self.get_tracking_uri())

        if self.tracking_username:
            os.environ[MLFLOW_TRACKING_USERNAME] = self.tracking_username
        if self.tracking_password:
            os.environ[MLFLOW_TRACKING_PASSWORD] = self.tracking_password
        if self.tracking_token:
            os.environ[MLFLOW_TRACKING_TOKEN] = self.tracking_token
        os.environ[MLFLOW_TRACKING_INSECURE_TLS] = (
            "true" if self.tracking_insecure_tls else "false"
        )

    def cleanup_pipeline_run(self) -> None:
        """Cleans up resources after the pipeline run is finished."""
        set_tracking_uri("")

    @property
    def validator(self) -> Optional["StackValidator"]:
        """Validates that the stack has a `LocalArtifactStore` if no tracking
        uri was specified."""
        if self.tracking_uri:
            # user specified a tracking uri, do nothing
            return None
        else:
            # try to fall back to a tracking uri inside the zenml artifact
            # store. this only works in case of a local artifact store, so we
            # make sure to prevent stack with other artifact stores for now
            return StackValidator(
                custom_validation_function=lambda stack: isinstance(
                    stack.artifact_store, LocalArtifactStore
                )
            )
