#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""ZenML pipeline-writing taskset for verifiers/prime-rl.

Importing this package has one deliberate side-effect: it applies the
ZenML runtime selection patch (see ``patch.py``) when
``ZENML_VERIFIERS_RUNTIME=1``. The import side-effect is the only
reliable injection point — prime-rl runs each environment in an
isolated env-server subprocess, and this package is the code that
subprocess imports.

verifiers' plugin loader requires exactly one Taskset subclass exported
via ``__all__``.
"""

from zenml_pipeline_writing import patch
from zenml_pipeline_writing.taskset import PipelineWritingTaskset

patch.apply()

__all__ = ["PipelineWritingTaskset"]
