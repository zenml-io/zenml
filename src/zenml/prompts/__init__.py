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
"""Simple prompt artifact and materializer for ZenML."""

from zenml.prompts.diff_utils import (
    compare_prompts,
    compare_text_outputs,
    create_text_diff,
    format_diff_for_console,
)
from zenml.prompts.prompt import Prompt, PromptType
from zenml.prompts.prompt_materializer import PromptMaterializer
from zenml.prompts.prompt_response import PromptResponse
from zenml.prompts.prompt_response_materializer import PromptResponseMaterializer

__all__ = [
    "Prompt",
    "PromptType",
    "PromptMaterializer",
    "PromptResponse",
    "PromptResponseMaterializer",
    # Diff utilities - core functionality
    "create_text_diff",
    "compare_prompts", 
    "compare_text_outputs",
    "format_diff_for_console",
]