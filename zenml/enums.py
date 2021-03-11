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

from enum import Enum


class PipelineStatusTypes(Enum):
    NotStarted = 1
    Failed = 2
    Succeeded = 3
    Running = 4


class GDPComponent(Enum):
    SplitGen = 1
    SplitStatistics = 2
    SplitSchema = 3
    Sequencer = 4
    SequencerStatistics = 5
    SequencerSchema = 6
    PreTransform = 7
    PreTransformStatistics = 8
    PreTransformSchema = 9
    Transform = 10
    Trainer = 11
    Evaluator = 12
    ResultPackager = 13
    ModelValidator = 14
    Deployer = 15
    DataGen = 16
    Inferrer = 17
    DataStatistics = 18
    DataSchema = 19
    Tokenizer = 20


class MLMetadataTypes(Enum):
    sqlite = 1
    mysql = 2
    mock = 3


class ArtifactStoreTypes(Enum):
    local = 1
    gcs = 2


class StepTypes(Enum):
    base = 1
    data = 2
    sequencer = 3
    preprocesser = 4
    split = 5
    trainer = 6
    evaluator = 7
    deployer = 8
    inferrer = 9


class GCPGPUTypes(Enum):
    K80 = 1
    V100 = 2
    P100 = 3


class ImagePullPolicy(Enum):
    Always = 1
    Never = 2
    IfNotPresent = 3
