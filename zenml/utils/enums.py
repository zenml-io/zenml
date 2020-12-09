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


class PipelineRunTypes(Enum):
    training = 1
    datagen = 2
    infer = 3
    test = 4
    eval = 5


class FunctionTypes(Enum):
    transform = 1
    model = 2


class TrainingTypes(Enum):
    gcaip = 1
    local = 2


class ServingTypes(Enum):
    gcaip = 1
    local = 2


class GDPComponent(Enum):
    SplitGen = 1
    SplitStatistics = 2
    SplitSchema = 3
    SequenceTransform = 4
    SequenceStatistics = 5
    SequenceSchema = 6
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


class MLMetadataTypes(Enum):
    sqlite = 1
    mysql = 2


class ArtifactStoreTypes(Enum):
    local = 1
    gcs = 2
