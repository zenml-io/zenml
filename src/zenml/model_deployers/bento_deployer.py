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
"""BentoML Deployer Class on top of the base_model_deployer."""

import bentoml
from base_model_deployer import BaseModelDeployer

class BentoModelDeployer(BaseModelDeployer):
    """
    The BentoModelDeployer serves as the abstraction layer on top of the BaseModelDeployer to support the 
    BentoML models in production.

    1. It acts as a ZenML BaseService registry, where every BaseService instance
    is used as an internal representation of a remote model server (see the
    `find_model_server` abstract method). To achieve this, it must be able to
    re-create the configuration of a BaseService from information that is
    persisted externally, alongside or even part of the remote model server
    configuration itself.

    2. The model deployer also defines methods that implement basic life-cycle
    management on remote model servers outside the coverage of a pipeline
    (see `stop_model_server`, `start_model_server` and `delete_model_server`).

    Arguments:
        BaseModelDeployer {_type_} -- BaseModelDeployer
    
    """

    