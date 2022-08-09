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
"""Initialization of the visualizers module.

The `visualizers` module offers a way of constructing and displaying
visualizations of steps and pipeline results. The `BaseVisualizer` class is at
the root of all the other visualizers, including options to view the results of
pipeline runs, steps and pipelines themselves.
"""

from zenml.visualizers.base_visualizer import BaseVisualizer

__all__ = [
    "BaseVisualizer",
]
