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
    """Raises exception when the `name` does not exist in the system but an
    action is being done that requires it to be present."""

    def __init__(self,
                 name='',
                 reason='',
                 message='{} does not exist! This might be due to: {}'):
        super().__init__(message.format(name, reason))


class AlreadyExistsException(Exception):
    """Raises exception when the `name` already exist in the system but an
    action is trying to create a resource with the same name."""

    def __init__(self,
                 name='',
                 resource_type=''):
        message = f'{resource_type} `{name}` already exists! Please use ' \
                  f'Repository.get_instance().get_{resource_type}_by_name' \
                  f'("{name}") to fetch it.'
        super().__init__(message)


class PipelineNotSucceededException(Exception):
    """Raises exception when trying to fetch artifacts from a not succeeded
    pipeline."""

    def __init__(self,
                 name='',
                 message='{} is not yet completed successfully.'):
        super().__init__(message.format(name))
