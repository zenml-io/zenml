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

import os

from zenml.utils.enums import GDPComponent

APP_NAME = 'zenml'
CONFIG_VERSION = '1'

COMPARISON_NOTEBOOK = 'comparison_notebook.ipynb'
EVALUATION_NOTEBOOK = 'evaluation_notebook.ipynb'

ACTIVE_USER = '_active_user'
ACTIVE_CONFIG = 'active_config'
ACTIVE_WORKSPACE = 'active_workspace'
ACTIVE_DATASOURCE_COMMIT = 'active_datasource_commit'
ACTIVE_ORCHESTRATOR = 'active_orchestrator'
ACTIVE_PROVIDER = 'active_provider'
TOKEN = 'token'

# env variables that modules consume from
ZENML_PIPELINE_CONFIG = 'ZENML_PIPELINE_CONFIG'
CE_CLOUD_JOB_PREFIX = 'CE_CLOUD_JOB_PREFIX'
ENV_KUBEFLOW_GCR = 'KUBEFLOW_GCR'
ENV_TRAINER_GCR = 'TRAINER_GCR'
ENV_ZENML_DEBUG = 'ZENML_DEBUG'

# images kubeflow sources from
GDP_IMAGE = os.getenv(ENV_KUBEFLOW_GCR)
TRAINER_IMAGE = os.getenv(ENV_TRAINER_GCR)

# TODO: [HIGH] Switch to default False before release
IS_DEBUG_ENV = os.getenv(ENV_ZENML_DEBUG, True)

# Pipeline related parameters
PREPROCESSING_FN = 'gdp.components.transform.transform_module.preprocessing_fn'
TRAINER_FN = 'gdp.components.trainer.trainer_module.run_fn'


# IMPORTANT: This should be ONLY Alphabets AND LESS than 30 characters long!
# NO other characters allowed. This is because the dataflow jobs are named
# after them to match these names while calculating cost and billing!


def get_component_mapping():
    from tfx.components.evaluator.component import Evaluator
    from tfx.components.pusher.component import Pusher
    from tfx.components.schema_gen.component import SchemaGen
    from tfx.components.statistics_gen.component import StatisticsGen

    from zenml.core.components.session_transform.sequence_transform import \
        SequenceTransform
    from zenml.core.components.split_gen.component import SplitGen
    from zenml.core.components.trainer.component import Trainer
    from zenml.core.components.transform.component import Transform
    from zenml.core.components.data_gen.component import DataGen

    return {
        GDPComponent.SplitGen.name: SplitGen.__name__,
        GDPComponent.SplitStatistics.name: StatisticsGen.__name__,
        GDPComponent.SplitSchema.name: SchemaGen.__name__,
        GDPComponent.SequenceTransform.name: SequenceTransform.__name__,
        GDPComponent.SequenceStatistics.name: StatisticsGen.__name__,
        GDPComponent.SequenceSchema.name: SchemaGen.__name__,
        GDPComponent.PreTransform.name: 'PreTransform',  # TODO: TBI
        GDPComponent.PreTransformStatistics.name: StatisticsGen.__name__,
        GDPComponent.PreTransformSchema.name: SchemaGen.__name__,
        GDPComponent.Transform.name: Transform.__name__,
        GDPComponent.Trainer.name: Trainer.__name__,
        GDPComponent.Evaluator.name: Evaluator.__name__,
        GDPComponent.Deployer.name: Pusher.__name__,
        GDPComponent.DataGen.name: DataGen.__name__,
    }
