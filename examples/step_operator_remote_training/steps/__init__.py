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
"""
## Exemplary Steps

Three very simple steps
"""
from .evaluator.evaluator_step import evaluator
from .importer.importer_step import digits_data_loader
from .remote_trainer.remote_trainer_step import remote_trainer

__all__ = ["digits_data_loader", "remote_trainer", "evaluator"]
