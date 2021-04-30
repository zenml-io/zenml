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
"""Definition of the Spark Processing Backend"""

import multiprocessing
from typing import Text, Optional, List

from zenml.backends.processing import ProcessingBaseBackend


class ProcessingSparkBackend(ProcessingBaseBackend):
    """
    Use this to run pipelines on Apache Spark.

    A dedicated processing backend can be used to efficiently process large
    amounts of incoming data in parallel, potentially distributed across
    multiple machines. This can happen on base processing backends as well
    as cloud-based variants like Google Cloud Dataflow. More powerful machines
    with higher core counts and clock speeds can be leveraged to increase
    processing throughput significantly.

    This backend is not implemented yet.
    """

    def __init__(self,
                 spark_rest_url: Text,
                 environment_type: Text = 'LOOPBACK',
                 environment_cache_millis: int = 1000000,
                 spark_submit_uber_jar: bool = True):

        self.spark_rest_url = spark_rest_url
        self.environment_type = environment_type
        self.environment_cache_millis = environment_cache_millis
        self.spark_submit_uber_jar = spark_submit_uber_jar

        try:
            parallelism = multiprocessing.cpu_count()
        except NotImplementedError:
            parallelism = 1
        self.sdk_worker_parallelism = parallelism

        super(ProcessingSparkBackend, self).__init__(
            environment_type=environment_type,
            environment_cache_millis=environment_cache_millis,
            spark_submit_uber_jar=spark_submit_uber_jar,
            spark_rest_url=self.spark_rest_url)

    def get_beam_args(self,
                      pipeline_name: Text = None,
                      pipeline_root: Text = None) -> Optional[List[Text]]:

        return [
            '--runner=SparkRunner',
            '--spark_rest_url=' + self.spark_rest_url,
            '--environment_type=' + self.environment_type,
            '--environment_cache_millis=' + str(self.environment_cache_millis),
            '--sdk_worker_parallelism=' + str(self.sdk_worker_parallelism),
            '--experiments=use_loopback_process_worker=True',
            '--experiments=pre_optimize=all',
            '--spark_submit_uber_jar']
