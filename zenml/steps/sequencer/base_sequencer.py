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

from abc import abstractmethod

from tensorflow_metadata.proto.v0.schema_pb2 import Schema
from tensorflow_metadata.proto.v0.statistics_pb2 import \
    DatasetFeatureStatisticsList

from zenml.steps import BaseStep
from zenml.enums import StepTypes


class BaseSequencerStep(BaseStep):
    """
    Base class for all sequencer steps. These steps are used to
    specify transformation and filling operations on timeseries datasets
    that occur before the data preprocessing takes place.
    """

    STEP_TYPE = StepTypes.sequencer.name

    def __init__(self,
                 statistics: DatasetFeatureStatisticsList = None,
                 schema: Schema = None,
                 **kwargs):
        """
        Base Sequencer constructor.

        This steps uses a beam pipeline to handle the data processing and the
        pipeline consists of a few steps, where the main logic for each
        datapoint can be summarized as follows:

            1 - Add a timestamp to the datapoint
            2 - Add a category key to the datapoint (optional)
            3 - Split your data into sessions based on a windowing strategy
            4 - Process the sessions to create sequences

        With the `abstractmethod`s listed below, you have the option to modify
        anyone of these steps.

        Args:
            statistics: Parsed statistics output of a preceding StatisticsGen.
            schema: Parsed schema output of a preceding SchemaGen.
        """

        super().__init__(**kwargs)

        self.statistics = statistics
        self.schema = schema

    @abstractmethod
    def get_timestamp_do_fn(self):
        """
        The process of sequencing is highly dependent on the format of your
        data. For instance, the timestamp of a single datapoint can be
        infused within the datapoint in various shapes or forms.

        It is impossible to find THE one solution which would be able to parse
        all the different variants of timestamps and that is why we exposed
        this method.

        Through this method, you have access to all of the instance
        variables of your step and all you have to do is to return an instance
        of a beam.DoFn which returns a TimestampedValue. You can check our
        StandardSequencer for a practical example.
        """
        pass

    @abstractmethod
    def get_category_do_fn(self):
        """
        In ZenML, you have the option to split your data based on a categorical
        feature before the actual sequencing happens. This is especially
        helpful if you are dealing with a joint dataset (i.e dataset featuring
        multiple assets in the field, but you want to sequence on an
        asset-level)

        Similar to get_timestamp_do_fn, you need to implement a method, which
        returns an instance of a beam.DoFn class. This beam.DoFn should be
        responsible for extracting the category of a datapoint and add it to
        the datapoint and return it. For a practical example, you can check our
        StandardSequencer.
        """
        # TODO: Implement a default method, in case categories are not used
        pass

    @abstractmethod
    def get_window(self):
        """
        This method needs to return the desired windowing strategy for the
        beam pipeline.
        """
        pass

    @abstractmethod
    def get_combine_fn(self):
        """
        Once the data is split into sessions (and possibly categories too),
        it needs to be processed in order to extract sequences from the
        sessions.

        This method needs to return an instance of beam.CombineFn class, which
        processes the accumulated datapoints and extracts desired sequences.
        You can check out our StandardSequencer for a practical example.
        """
        pass
