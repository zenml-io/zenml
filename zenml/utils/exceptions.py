#  Copyright (c) maiot GmbH 2020. All Rights Reserved.
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
"""ZenML specific exception definitions"""


class InitializationException(Exception):
    """Raises exception when a function is run before zenml initialization."""

    def __init__(self,
                 message='ZenML config is none. Did you do `zenml init`?'):
        super().__init__(message)


class EmptyDatasourceException(Exception):
    """Raises exception when a datasource data is accessed without running
    an associated pipeline."""

    def __init__(self,
                 message='This datasource has not been used in any '
                         'pipelines, therefore the associated data has no '
                         'versions. Please use this datasouce in any ZenML '
                         'pipeline with `pipeline.add_datasource('
                         'datasource)`'):
        super().__init__(message)


class DoesNotExistException(Exception):
    """Raises exception when the `name` does not exist in the system."""

    def __init__(self,
                 name='',
                 reason='',
                 message='{} does not exist! This might be due to: {}'):
        super().__init__(message.format(name, reason))
