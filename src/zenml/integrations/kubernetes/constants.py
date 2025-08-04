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
#
# Parts of the `prepare_or_run_pipeline()` method of this file are
# inspired by the Kubernetes dag runner implementation of tfx
"""Kubernetes orchestrator constants."""

ENV_ZENML_KUBERNETES_RUN_ID = "ZENML_KUBERNETES_RUN_ID"
KUBERNETES_SECRET_TOKEN_KEY_NAME = "zenml_api_token"
KUBERNETES_CRON_JOB_METADATA_KEY = "cron_job_name"
# Annotation keys
ORCHESTRATOR_ANNOTATION_KEY = "zenml.io/orchestrator"
RUN_ID_ANNOTATION_KEY = "zenml.io/run-id"
ORCHESTRATOR_RUN_ID_ANNOTATION_KEY = "zenml.io/orchestrator-run-id"
STEP_NAME_ANNOTATION_KEY = "zenml.io/step-name"
STEP_OPERATOR_ANNOTATION_KEY = "zenml.io/step-operator"
