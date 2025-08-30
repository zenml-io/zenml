#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""ZenML Pipeline Serving module.

This module provides functionality to serve ZenML pipelines as FastAPI endpoints,
enabling real-time execution of ML pipelines, AI agents, and multi-agent systems
through HTTP/WebSocket APIs.

For capture mode configuration, use:
    from zenml.serving.policy import CapturePolicyMode  # Enum values
    from zenml.serving.capture import Cap  # Convenience constants
"""

try:
    from zenml.serving.service import PipelineServingService
    
    __all__ = [
        "PipelineServingService",
    ]
        
except ImportError:
    # Handle case where optional dependencies might not be available
    __all__ = []