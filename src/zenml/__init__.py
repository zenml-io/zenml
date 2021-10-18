#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
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

import os  # noqa

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(ROOT_DIR, "VERSION")) as version_file:
    __version__ = version_file.read().strip()

from zenml.logger import init_logging  # noqa
from zenml.pipelines.pipeline_decorator import pipeline  # noqa
from zenml.steps.step_decorator import step  # noqa
from zenml.utils.analytics_utils import initialize_telemetry

init_logging()
initialize_telemetry()
