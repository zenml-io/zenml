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

from zenml.steps.sequencer.standard_sequencer.methods import \
    methods_resampling, methods_filling
from zenml.utils.preprocessing_utils import MethodDescriptions


class ResamplingMethods(MethodDescriptions):
    MODES = {'mean': (methods_resampling.resample_mean, []),
             'threshold': (methods_resampling.resample_thresholding,
                           ['cond', 'c_value', 'threshold', 'set_value']),
             'mode': (methods_resampling.resample_mode, []),
             'median': (methods_resampling.resample_median, [])}


class FillingMethods(MethodDescriptions):
    MODES = {'forward': (methods_filling.forward_f, []),
             'backwards': (methods_filling.backwards_f, []),
             'min': (methods_filling.min_f, []),
             'max': (methods_filling.max_f, []),
             'mean': (methods_filling.mean_f, []),
             'custom': (methods_filling.custom_f, ['custom_value'])}
