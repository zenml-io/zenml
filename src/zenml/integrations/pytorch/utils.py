#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""PyTorch utils."""

from typing import Dict

import torch


def count_module_params(module: torch.nn.Module) -> Dict[str, int]:
    """Get the total and trainable parameters of a module.

    Args:
        module: The module to get the parameters of.

    Returns:
        A dictionary with the total and trainable parameters.
    """
    total_params = sum([param.numel() for param in module.parameters()])
    trainable_params = sum(
        [param.numel() for param in module.parameters() if param.requires_grad]
    )
    return {
        "num_params": total_params,
        "num_trainable_params": trainable_params,
    }
