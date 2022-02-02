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
    """This is a step context extension that can be used to facilitate whylogs
    data logging and profiling inside a step function.

    It acts as a wrapper built around the whylogs API that transparently
    incorporates ZenML specific information into the generated whylogs dataset
    profiles that can be used to associate whylogs profiles with the
    corresponding ZenML step run that produces them.

    It also simplifies the whylogs profile generation process by abstracting
    away some of the whylogs specific details, such as whylogs session and
    logger initialization and management.
    """

    _session: Session = None

    def __init__(
        self,
        step_context: StepContext,
        project: Optional[str] = None,
        pipeline: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """Create a ZenML whylogs context based on a generic step context.

        Args:
            step_context: a StepContext instance that provides information
                about the currently running step, such as the step name
            project: optional project name to use for the whylogs session
            pipeline: optional pipeline name to use for the whylogs session
            tags: optional list of tags to apply to all whylogs profiles
                generated through this context
        """
        self._step_context = step_context
        self._project = project
        self._pipeline = pipeline
        self._tags = tags

    def get_whylogs_session(
        self,
    ) -> Session:
        """Get the whylogs session associated with the current step.

        Returns:
            The whylogs Session instance associated with the current step
        """
        if self._session is not None:
            return self._session

        self._session = Session(
            project=self._project or self._step_context.step_name,
            pipeline=self._pipeline or self._step_context.step_name,
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
        # TODO [ENG-437]: use a default whylogs dataset_name that is unique across
        #  multiple pipelines
        dataset_name = dataset_name or self._step_context.step_name
        final_tags = self._tags.copy() if self._tags else dict()
        # TODO [ENG-438]: add more zenml specific tags to the whylogs profile, such
        #  as the pipeline name and run ID
        final_tags["zenml.step"] = self._step_context.step_name
        # the datasetId tag is used to identify dataset profiles in whylabs.
        # dataset profiles with the same datasetID are considered to belong
        # to the same dataset/model.
        final_tags.setdefault("datasetId", dataset_name)
        if tags:
            final_tags.update(tags)
        logger = session.logger(
            dataset_name, dataset_timestamp=dataset_timestamp, tags=final_tags
        )
        logger.log_dataframe(df)
        return logger.close()
