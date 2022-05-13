#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
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
"""
An orchestrator is a special kind of backend that manages the running of each
step of the pipeline. Orchestrators administer the actual pipeline runs. You can
think of it as the 'root' of any pipeline job that you run during your
experimentation.

ZenML supports a local orchestrator out of the box which allows you to run your
pipelines in a local environment. We also support using Apache Airflow as the
orchestrator to handle the steps of your pipeline.
"""
from zenml.orchestrators.base_orchestrator import BaseOrchestrator
from zenml.orchestrators.local.local_orchestrator import LocalOrchestrator

__all__ = ["BaseOrchestrator", "LocalOrchestrator"]
