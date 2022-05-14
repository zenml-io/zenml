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
Data Analyzers are stack components that analyze data as they flow through the 
pipeline. A good example of a data analyzer is a drift detection component that 
detects drift, or a data quality assesment component.
"""

from zenml.data_analyzer.base_data_analyzer import BaseDataAnalyzer

__all__ = [
    "BaseDataAnalyzer",
]
