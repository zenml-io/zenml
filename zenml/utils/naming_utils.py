#  Copyright (c) maiot GmbH 2021. All Rights Reserved.
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

"""
This collection of utility functions is aiming to help the users follow a
certain pre-defined naming paradigm.

However, due to the highly dynamic nature of ML tasks, users might need to
implement their own naming scheme depending on their tasks.
"""

from typing import Text

TRANSFORM_SUFFIX = '_xf'
LABEL_SUFFIX = '_xl'
OUTPUT_SUFFIX = '_o'


def transformed_feature_name(name: Text):
    return name + TRANSFORM_SUFFIX


def transformed_label_name(name: Text):
    return name + LABEL_SUFFIX


def output_name(name: Text):
    return name + OUTPUT_SUFFIX


def check_if_transformed_feature(name: Text):
    return name.endswith(TRANSFORM_SUFFIX)


def check_if_transformed_label(name: Text):
    return name.endswith(LABEL_SUFFIX)


def check_if_output_name(name: Text):
    return name.endswith(OUTPUT_SUFFIX)
