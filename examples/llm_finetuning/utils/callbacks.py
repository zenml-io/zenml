# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2024. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from typing import Dict

from transformers import (
    TrainerCallback,
    TrainerControl,
    TrainerState,
    TrainingArguments,
)

from zenml import get_step_context


class ZenMLCallback(TrainerCallback):
    """Callback that logs metrics to ZenML."""

    def on_evaluate(
        self,
        args: TrainingArguments,
        state: TrainerState,
        control: TrainerControl,
        metrics: Dict[str, float],
        **kwargs,
    ):
        """Log metrics to the ZenML Model version as metadata.

        Args:
            args: The training arguments.
            state: The trainer state.
            control: The trainer control.
            metrics: The metrics to log.
        """
        try:
            context = get_step_context()
            context.model.log_metadata(
                {
                    f"step_{state.global_step}_eval_metrics": metrics,
                }
            )
        except RuntimeError:
            # If we can't get the context, silently pass
            return

    def on_save(
        self,
        args: TrainingArguments,
        state: TrainerState,
        control: TrainerControl,
        **kwargs,
    ):
        # TODO: add ability to save model checkpoints here, will likely get redundant with Mounts
        pass
