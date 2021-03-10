#  Copyright (c) maiot GmbH 2020. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Entrypoint for gcp orchestrator"""

import base64
import json
import os
import sys

import fire

from zenml.backends.orchestrator.base.orchestrator_base_backend import \
    OrchestratorBaseBackend
from zenml.backends.orchestrator.gcp.orchestrator_gcp_backend import \
    TAR_PATH_ARG
from zenml.repo.repo import Repository
from zenml.standards import standard_keys as keys
from zenml.utils import path_utils

EXTRACTED_TAR_DIR_NAME = 'zenml_working.tar.gz'
EXTRACTED_TAR_FILE_PATH = os.path.join(os.getcwd(), EXTRACTED_TAR_DIR_NAME)
EXTRACTED_TAR_DIR = os.path.join(os.getcwd(), 'zenml_working')


class PipelineRunner(object):

    def run_pipeline(self, config_b64: str):
        # Load config from base64
        config = json.loads(base64.b64decode(config_b64))

        # Remove tar_path arg from config
        tar_path = config[keys.GlobalKeys.BACKEND][keys.BackendKeys.ARGS].pop(
            TAR_PATH_ARG)

        # Copy it over locally because it will be remote
        path_utils.copy(tar_path, EXTRACTED_TAR_FILE_PATH)

        # Extract it to EXTRACTED_TAR_DIR
        path_utils.extract_tarfile(EXTRACTED_TAR_FILE_PATH, EXTRACTED_TAR_DIR)

        # Append to sys to make user code discoverable
        sys.path.append(EXTRACTED_TAR_DIR)

        # Make sure the Repository is initialized at the right path
        Repository.get_instance(EXTRACTED_TAR_DIR)

        # Change orchestrator of pipeline to local
        OrchestratorBaseBackend().run(config)


if __name__ == "__main__":
    # execute only if run as a script
    fire.Fire(PipelineRunner)
