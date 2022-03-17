# Copyright 2021 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""An abstract class for the Trainer for both CAIP and Vertex."""

import abc
import datetime
import json
import random
from typing import Any, Dict, List, Optional, Union

from absl import logging
from google.cloud.aiplatform import gapic
from google.cloud.aiplatform_v1.types.custom_job import CustomJob
from google.cloud.aiplatform_v1.types.job_state import JobState
from googleapiclient import discovery

from tfx import types
from tfx.types import artifact_utils
from tfx.utils import telemetry_utils
from tfx.utils import version_utils

# Default container image being used for CAIP training jobs.
_TFX_IMAGE = "gcr.io/tfx-oss-public/tfx:{}".format(
    version_utils.get_image_version()
)

# Entrypoint of cloud AI platform training. The module comes from `tfx`
# package installation into a default location of 'python'.
_CONTAINER_COMMAND = ["python", "-m", "tfx.scripts.run_executor"]

_VERTEX_ENDPOINT_SUFFIX = "-aiplatform.googleapis.com"

_VERTEX_JOB_STATE_SUCCEEDED = JobState.JOB_STATE_SUCCEEDED
_VERTEX_JOB_STATE_FAILED = JobState.JOB_STATE_FAILED
_VERTEX_JOB_STATE_CANCELLED = JobState.JOB_STATE_CANCELLED


class AbstractJobClient(abc.ABC):
    """Abstract class interacting with CAIP CMLE job or Vertex CustomJob."""

    JOB_STATES_COMPLETED = ()  # Job states for success, failure or cancellation
    JOB_STATES_FAILED = ()  # Job states for failure or cancellation

    def __init__(self):
        self.create_client()
        self._job_name = ""  # Assigned in self.launch_job()

    @abc.abstractmethod
    def create_client(self) -> None:
        """Creates the job client.

        Can also be used for recreating the job client (e.g. in the case of
        communication failure).

        Multiple job requests can be done in parallel if needed, by creating an
        instance of the class for each job. Note that one class instance should
        only be used for one job, as each instance stores variables (e.g. job_id)
        specific to each job.
        """
        pass

    @abc.abstractmethod
    def create_training_job(
        self,
        input_dict,
        output_dict,
        exec_properties,
        executor_class_path,
        job_args,
        job_id,
    ) -> Dict[str, Any]:
        """Get training args for runner._launch_aip_training.

        The training args contain the inputs/outputs/exec_properties to the
        tfx.scripts.run_executor module.

        Args:
          input_dict: Passthrough input dict for tfx.components.Trainer.executor.
          output_dict: Passthrough input dict for tfx.components.Trainer.executor.
          exec_properties: Passthrough input dict for
            tfx.components.Trainer.executor.
          executor_class_path: class path for TFX core default trainer.
          job_args: Training input argument for AI Platform training job.
          job_id: Job ID for AI Platform Training job. If not supplied,
            system-determined unique ID is given.

        Returns:
          A dict containing the training arguments
        """
        pass

    @abc.abstractmethod
    def launch_job(self, project: str, training_job: Dict[str, Any]) -> None:
        """Launches a long-running job.

        Args:
          project: The project name in the form of 'projects/{project_id}'
          training_job: A Cloud training job. For CAIP, See
            https://cloud.google.com/ml-engine/reference/rest/v1/projects.jobs for
              the detailed schema. for Vertex AI Training, see
            https://cloud.google.com/vertex-ai/docs/reference/rest/v1/projects.locations.customJobs#CustomJob
              the detailed schema.
        """
        pass

    @abc.abstractmethod
    def get_job(self) -> Union[Dict[str, str], CustomJob]:
        """Gets the the long-running job."""
        pass

    @abc.abstractmethod
    def get_job_state(
        self, response: Union[Dict[str, str], CustomJob]
    ) -> Union[str, JobState]:
        """Gets the state of the long-running job.

        Args:
          response: The response from get_job

        Returns:
          The job state.
        """
        pass

    def get_job_name(self) -> str:
        """Gets the job name."""
        return self._job_name

    def generate_container_command(
        self,
        input_dict: Dict[str, List[types.Artifact]],
        output_dict: Dict[str, List[types.Artifact]],
        exec_properties: Dict[str, Any],
        executor_class_path: str,
    ) -> List[str]:
        """Generate container command to run executor."""
        json_inputs = artifact_utils.jsonify_artifact_dict(input_dict)
        logging.info("json_inputs='%s'.", json_inputs)
        json_outputs = artifact_utils.jsonify_artifact_dict(output_dict)
        logging.info("json_outputs='%s'.", json_outputs)
        json_exec_properties = json.dumps(exec_properties, sort_keys=True)
        logging.info("json_exec_properties='%s'.", json_exec_properties)

        # We use custom containers to launch training on AI Platform, which invokes
        # the specified image using the container's entrypoint. The default
        # entrypoint for TFX containers is to call scripts/run_executor.py. The
        # arguments below are passed to this run_executor entry to run the executor
        # specified in `executor_class_path`.
        return _CONTAINER_COMMAND + [
            "--executor_class_path",
            executor_class_path,
            "--inputs",
            json_inputs,
            "--outputs",
            json_outputs,
            "--exec-properties",
            json_exec_properties,
        ]


class CAIPJobClient(AbstractJobClient):
    """Class for interacting with CAIP CMLE job."""

    JOB_STATES_COMPLETED = ("SUCCEEDED", "FAILED", "CANCELLED")
    JOB_STATES_FAILED = ("FAILED", "CANCELLED")

    def create_client(self) -> None:
        """Creates the discovery job client.

        Can also be used for recreating the job client (e.g. in the case of
        communication failure).

        Multiple job requests can be done in parallel if needed, by creating an
        instance of the class for each job. Note that one class instance should
        only be used for one job, as each instance stores variables (e.g. job_id)
        specific to each job.
        """
        self._client = discovery.build(
            "ml",
            "v1",
            requestBuilder=telemetry_utils.TFXHttpRequest,
        )

    def create_training_job(
        self,
        input_dict: Dict[str, List[types.Artifact]],
        output_dict: Dict[str, List[types.Artifact]],
        exec_properties: Dict[str, Any],
        executor_class_path: str,
        job_args: Dict[str, Any],
        job_id: Optional[str],
    ) -> Dict[str, Any]:
        """Get training args for runner._launch_aip_training.

        The training args contain the inputs/outputs/exec_properties to the
        tfx.scripts.run_executor module.

        Args:
          input_dict: Passthrough input dict for tfx.components.Trainer.executor.
          output_dict: Passthrough input dict for tfx.components.Trainer.executor.
          exec_properties: Passthrough input dict for
            tfx.components.Trainer.executor.
          executor_class_path: class path for TFX core default trainer.
          job_args: Training input argument for AI Platform training job.
            'pythonModule', 'pythonVersion' and 'runtimeVersion' will be inferred.
            For the full set of parameters, refer to
            https://cloud.google.com/ml-engine/reference/rest/v1/projects.jobs#TrainingInput
          job_id: Job ID for AI Platform Training job. If not supplied,
            system-determined unique ID is given. Refer to
          https://cloud.google.com/ml-engine/reference/rest/v1/projects.jobs#resource-job

        Returns:
          A dict containing the training arguments
        """
        training_inputs = job_args.copy()

        container_command = self.generate_container_command(
            input_dict, output_dict, exec_properties, executor_class_path
        )

        if not training_inputs.get("masterConfig"):
            training_inputs["masterConfig"] = {
                "imageUri": _TFX_IMAGE,
            }

        # Always use our own entrypoint instead of relying on container default.
        if "containerCommand" in training_inputs["masterConfig"]:
            logging.warn("Overriding custom value of containerCommand")
        training_inputs["masterConfig"]["containerCommand"] = container_command

        with telemetry_utils.scoped_labels(
            {telemetry_utils.LABEL_TFX_EXECUTOR: executor_class_path}
        ):
            job_labels = telemetry_utils.make_labels_dict()

        # 'tfx_YYYYmmddHHMMSS' is the default job ID if not explicitly specified.
        job_id = job_id or "tfx_{}".format(
            datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        )

        caip_job = {
            "job_id": job_id,
            "training_input": training_inputs,
            "labels": job_labels,
        }

        return caip_job

    def launch_job(self, project: str, training_job: Dict[str, Any]) -> None:
        """Launches a long-running job.

        Args:
          project: The GCP project under which the training job will be executed.
          training_job: A Cloud AI Platform training job. See
            https://cloud.google.com/ml-engine/reference/rest/v1/projects.jobs for
              the detailed schema.
        """

        parent = "projects/{}".format(project)

        # Submit job to AIP Training
        logging.info("TrainingJob=%s", training_job)
        logging.info(
            "Submitting job='%s', project='%s' to AI Platform.",
            training_job["job_id"],
            parent,
        )
        request = (
            self._client.projects()
            .jobs()
            .create(body=training_job, parent=parent)
        )
        self._job_name = "{}/jobs/{}".format(parent, training_job["job_id"])
        request.execute()

    def get_job(self) -> Dict[str, str]:
        """Gets the long-running job."""
        request = self._client.projects().jobs().get(name=self._job_name)
        return request.execute()

    def get_job_state(self, response) -> str:
        """Gets the state of the long-running job.

        Args:
          response: The response from get_job

        Returns:
          The job state.
        """
        return response["state"]


class VertexJobClient(AbstractJobClient):
    """Class for interacting with Vertex CustomJob."""

    JOB_STATES_COMPLETED = (
        _VERTEX_JOB_STATE_SUCCEEDED,
        _VERTEX_JOB_STATE_FAILED,
        _VERTEX_JOB_STATE_CANCELLED,
    )
    JOB_STATES_FAILED = (_VERTEX_JOB_STATE_FAILED, _VERTEX_JOB_STATE_CANCELLED)

    def __init__(self, vertex_region: str):
        if vertex_region is None:
            raise ValueError("Please specify a region for Vertex training.")
        self._region = vertex_region
        super().__init__()

    def create_client(self) -> None:
        """Creates the Gapic job client.

        Can also be used for recreating the job client (e.g. in the case of
        communication failure).

        Multiple job requests can be done in parallel if needed, by creating an
        instance of the class for each job. Note that one class instance should
        only be used for one job, as each instance stores variables (e.g. job_id)
        specific to each job.
        """
        self._client = gapic.JobServiceClient(
            client_options=dict(
                api_endpoint=self._region + _VERTEX_ENDPOINT_SUFFIX
            )
        )

    def create_training_job(
        self,
        input_dict: Dict[str, List[types.Artifact]],
        output_dict: Dict[str, List[types.Artifact]],
        exec_properties: Dict[str, Any],
        executor_class_path: str,
        job_args: Dict[str, Any],
        job_id: Optional[str],
    ) -> Dict[str, Any]:
        """Get training args for runner._launch_aip_training.

        The training args contain the inputs/outputs/exec_properties to the
        tfx.scripts.run_executor module.

        Args:
          input_dict: Passthrough input dict for tfx.components.Trainer.executor.
          output_dict: Passthrough input dict for tfx.components.Trainer.executor.
          exec_properties: Passthrough input dict for
            tfx.components.Trainer.executor.
          executor_class_path: class path for TFX core default trainer.
          job_args: CustomJob for Vertex AI custom training. See
            https://cloud.google.com/vertex-ai/docs/reference/rest/v1/projects.locations.customJobs#CustomJob
              for the detailed schema.
            [Deprecated]: job_args also support specifying only the CustomJobSpec
              instead of CustomJob. However, this functionality is deprecated.
          job_id: Display name for AI Platform (Unified) custom training job. If not
            supplied, system-determined unique ID is given. Refer to
            https://cloud.google.com/vertex-ai/docs/reference/rest/v1/projects.locations.customJobs#CustomJob

        Returns:
          A dict containing the Vertex AI CustomJob
        """
        job_args = job_args.copy()
        if job_args.get("job_spec"):
            custom_job_spec = job_args["job_spec"]
        else:
            logging.warn(
                "job_spec key was not found. Parsing job_args as CustomJobSpec instead"
            )
            custom_job_spec = job_args

        container_command = self.generate_container_command(
            input_dict, output_dict, exec_properties, executor_class_path
        )

        if not custom_job_spec.get("worker_pool_specs"):
            custom_job_spec["worker_pool_specs"] = [{}]

        for worker_pool_spec in custom_job_spec["worker_pool_specs"]:
            if not worker_pool_spec.get("container_spec"):
                worker_pool_spec["container_spec"] = {
                    "image_uri": _TFX_IMAGE,
                }

            # Always use our own entrypoint instead of relying on container default.
            if "command" in worker_pool_spec["container_spec"]:
                logging.warn(
                    "Overriding custom value of container_spec.command"
                )
            worker_pool_spec["container_spec"]["command"] = container_command

        # 'tfx_YYYYmmddHHMMSS_xxxxxxxx' is the default job display name if not
        # explicitly specified.
        job_id = job_args.get("display_name", job_id)
        job_id = job_id or "tfx_{}_{}".format(
            datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
            "%08x" % random.getrandbits(32),
        )

        with telemetry_utils.scoped_labels(
            {telemetry_utils.LABEL_TFX_EXECUTOR: executor_class_path}
        ):
            job_labels = telemetry_utils.make_labels_dict()
        job_labels.update(job_args.get("labels", {}))

        encryption_spec = job_args.get("encryption_spec", {})

        custom_job = {
            "display_name": job_id,
            "job_spec": custom_job_spec,
            "labels": job_labels,
            "encryption_spec": encryption_spec,
        }

        return custom_job

    def launch_job(self, project: str, training_job: Dict[str, Any]) -> None:
        """Launches a long-running job.

        Args:
          project: The GCP project under which the training job will be executed.
          training_job: A CustomJob for AI Platform (Unified). See
            https://cloud.google.com/vertex-ai/docs/reference/rest/v1/projects.locations.customJobs#CustomJob
              the detailed schema.
        """

        parent = "projects/{project}/locations/{location}".format(
            project=project, location=self._region
        )

        logging.info("TrainingJob=%s", training_job)
        logging.info(
            "Submitting custom job='%s', parent='%s' to Vertex AI Training.",
            training_job["display_name"],
            parent,
        )
        response = self._client.create_custom_job(
            parent=parent, custom_job=training_job
        )
        self._job_name = response.name

    def get_job(self) -> CustomJob:
        """Gets the long-running job."""
        return self._client.get_custom_job(name=self._job_name)

    def get_job_state(self, response) -> JobState:
        """Gets the state of the long-running job.

        Args:
          response: The response from get_job

        Returns:
          The job state.
        """
        return response.state


def get_job_client(
    enable_vertex: Optional[bool] = False, vertex_region: Optional[str] = None
) -> Union[CAIPJobClient, VertexJobClient]:
    """Gets the job client.

    Args:
      enable_vertex: Whether to enable Vertex
      vertex_region: Region for training endpoint in Vertex. Defaults to
        'us-central1'.

    Returns:
      The corresponding job client.
    """
    if enable_vertex:
        return VertexJobClient(vertex_region)
    return CAIPJobClient()
