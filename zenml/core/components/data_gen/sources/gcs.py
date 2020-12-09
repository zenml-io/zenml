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

import re
from typing import Text, Dict, Any

import apache_beam as beam
from google.cloud import storage
from google.oauth2 import service_account as sa_service
from tfx.types.component_spec import ExecutionParameter

from zenml.core.components.data_gen.sources.interface import SourceInterface


@beam.ptransform_fn
@beam.typehints.with_input_types(beam.Pipeline)
@beam.typehints.with_output_types(beam.typehints.Dict[Text, Any])
class BlobToBytes(beam.DoFn):
    def __init__(self, service_account):
        """This is the only way to not do crazy client instantiation cycles.

        Args:
            service_account:
        """
        self._sa = service_account

    def parse_gcs_path(self, gcs_path, object_optional=False):
        """Return the bucket and object names of the given gs:// path.

        Args:
            gcs_path:
            object_optional:
        """
        match = re.match('^gs://([^/]+)/(.*)$', gcs_path)
        if match is None or (match.group(2) == '' and not object_optional):
            raise ValueError(
                'GCS path must be in the form gs://<bucket>/<object>.')
        return match.group(1), match.group(2)

    def start_bundle(self):
        self.credentials = sa_service.Credentials.from_service_account_info(
            self._sa)
        self.gcs_client = storage.Client(credentials=self.credentials)

    def process(self, element):
        """Parse the blob and convert to TFExample

        Args:
            element:
        """
        bucket_name, blob_name = self.parse_gcs_path(element)
        bucket = self.gcs_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob_as_bstring = blob.download_as_string()
        return [blob_as_bstring]


class GCSInjection(SourceInterface):
    def get_config_spec(self):
        return {'input_path': ExecutionParameter(type=Text),
                'service_account': ExecutionParameter(type=Dict[Text, Any])}

    def config_parser(self, config):
        """
        Args:
            config:
        """
        return config

    def beam_transform(self, pipeline, exec_properties):
        """
        Args:
            pipeline:
            exec_properties:
        """
        input_path = exec_properties['input_path']
        service_account = exec_properties['service_account']

        result = (pipeline
                  | beam.io.ReadFromText(input_path)
                  | beam.ParDo(BlobToBytes(service_account))
                  )
        return result
