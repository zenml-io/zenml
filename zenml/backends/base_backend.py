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
"""Definition of a the base Backend"""

from typing import Dict

from zenml.logger import get_logger
from zenml.standards.standard_keys import BackendKeys
from zenml.utils import source_utils
from zenml.utils.print_utils import to_pretty_string, PrintStyles

logger = get_logger(__name__)


class BaseBackend:
    """
    Base class for all ZenML backends.

    Every ZenML pipeline runs in backends that defines where and how the
    pipeline runs. Override this base class to define your own custom Pipeline
    backend.

    There are three types of backends available in ZenML: Orchestration
    backends, processing backends and training backends. Each of them serve
    different purposes in different stages of the pipeline.
    An orchestration backend is useful for scheduling and executing the
    different pipeline components.

    A dedicated processing backend can be used to efficiently process large
    amounts of incoming data in parallel, potentially distributed across
    multiple machines. This can happen on local processing backends as well
    as cloud-based variants like Google Cloud Dataflow. More powerful machines
    with higher core counts and clock speeds can be leveraged to increase
    processing throughput significantly.

    A training backend can be used to efficiently train a machine learning
    model on large amounts of data. Since most common machine learning models
    leverage mainly linear algebra operations under the hood, they can
    potentially benefit a lot from dedicated training hardware like Graphics
    Processing Units (GPUs) or application-specific integrated circuits
    (ASICs). Again, local training backends or cloud-based training backends
    like Google Cloud AI Platform (GCAIP) with or without GPU/ASIC support
    can be used.
    """
    BACKEND_TYPE = None

    def __init__(self, **kwargs):
        if len(kwargs):
            self._kwargs = kwargs
        else:
            self._kwargs = {}

        self._source = source_utils.resolve_class(self.__class__)
        self._immutable = False

    def __str__(self):
        return to_pretty_string(self.to_config())

    def __repr__(self):
        return to_pretty_string(self.to_config(), style=PrintStyles.PPRINT)

    def to_config(self):
        """Converts Backend to ZenML config block."""
        return {
            BackendKeys.TYPE: self.BACKEND_TYPE,
            BackendKeys.ARGS: self._kwargs,  # everything in init
            BackendKeys.SOURCE: self._source,
        }

    @classmethod
    def from_config(cls, config: Dict):
        """
        Convert from ZenML config dict to ZenML Backend object.

        Args:
            config: a ZenML config in dict-form (probably loaded from YAML)
        """
        backend_class = source_utils.load_source_path_class(
            config[BackendKeys.SOURCE])
        backend_args = config[BackendKeys.ARGS]
        obj = backend_class(**backend_args)
        obj._immutable = True
        return obj
