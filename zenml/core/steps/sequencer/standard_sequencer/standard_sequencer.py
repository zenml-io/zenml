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

from typing import Dict, Text

from zenml.core.steps.sequencer.base_sequencer import BaseSequencerStep

from zenml.core.steps.sequencer.standard_sequencer.methods \
    .standard_methods import ResamplingMethods, FillingMethods
from zenml.utils.preprocessing_utils import parse_methods


class StandardSequencer(BaseSequencerStep):

    def __init__(self,
                 timestamp_column: Text,
                 overwrite: Dict[Text, Text] = None,

                 gap_threshold: int = 60000,
                 sequence_length: int = 16,
                 resampling_rate: int = 1000,
                 sequence_shift: int = 1,
                 category_column: Text = None,
                 **kwargs):

        self.timestamp_column = timestamp_column
        self.category_column = category_column
        self.gap_threshold = gap_threshold
        self.overwrite = overwrite
        self.sequence_length = sequence_length
        self.sequence_shift = sequence_shift
        self.resampling_rate = resampling_rate

        self.resampling_dict = parse_methods(overwrite or {},
                                             'resampling',
                                             ResamplingMethods)

        self.filling_dict = parse_methods(overwrite or {},
                                          'filling',
                                          FillingMethods)

        super(StandardSequencer, self).__init__(**kwargs)
