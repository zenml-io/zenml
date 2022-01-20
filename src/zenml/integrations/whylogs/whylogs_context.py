#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
import datetime
from typing import Dict, Optional

import pandas as pd
from whylogs import DatasetProfile  # type: ignore
from whylogs.app import Session  # type: ignore

from zenml.steps.step_context import StepContext


class WhylogsContext:
    """Step context extension used to facilitate whylogs data logging and profiling
    inside a step function.
    """

    _session: Session = None

    def __init__(self, step_context: StepContext) -> None:
        self._step_context = step_context

    def get_whylogs_session(
        self,
    ) -> Session:
        """Returns the whylogs session associated with the current step.

        Args:
            output_name: Optional name of the output for which to get the
                materializer. If no name is given and the step only has a
                single output, the materializer of this output will be
                returned. If the step has multiple outputs, an exception
                will be raised.
            custom_materializer_class: If given, this `BaseMaterializer`
                subclass will be initialized with the output artifact instead
                of the materializer that was registered for this step output.

        Returns:
            A materializer initialized with the output artifact for
            the given output.
        """
        if self._session is not None:
            return self._session

        self._session = Session(
            project=self._step_context.step_name,
            pipeline=self._step_context.step_name,
            # keeping the writers list empty, serialization is done in the
            # materializer
            writers=[],
        )

        return self._session

    def profile_dataframe(
        self,
        df: pd.DataFrame,
        dataset_name: Optional[str] = None,
        dataset_timestamp: Optional[datetime.datetime] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> DatasetProfile:
        """Generate whylogs statistics for a Pandas dataframe.

        Args:
            df: a Pandas dataframe to profile.
            dataset_name: the name of the dataset (Optional). If not specified,
                the pipeline step name is used
            dataset_timestamp: timestamp to associate with the generated
                dataset profile (Optional). The current time is used if not
                supplied.
            tags: custom metadata tags associated with the whylogs profile

        Returns:
            A whylogs DatasetProfile with the statistics generated from the
            input dataset.
        """
        session = self.get_whylogs_session()
        # TODO [LOW]: use a default whylogs dataset_name that is unique across
        #  multiple pipelines
        dataset_name = dataset_name or self._step_context.step_name
        tags = tags or dict()
        # TODO [LOW]: add more zenml specific tags to the whylogs profile, such
        #  as the pipeline name and run ID
        tags["zenml.step"] = self._step_context.step_name
        # the datasetId tag is used to identify dataset profiles in whylabs.
        # dataset profiles with the same datasetID are considered to belong
        # to the same dataset/model.
        tags.setdefault("datasetId", dataset_name)
        logger = session.logger(
            dataset_name, dataset_timestamp=dataset_timestamp, tags=tags
        )
        logger.log_dataframe(df)
        return logger.close()
