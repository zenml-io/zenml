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

import os
import re
from typing import Text, Dict, Any, Tuple

import apache_beam as beam
from google.cloud import storage
from google.oauth2 import service_account as sa_service

from zenml.core.components.data_gen.constants import BINARY_DATA, FILE_NAME, \
    BASE_PATH, FILE_PATH, FILE_EXT
from zenml.core.components.data_gen.constants import GCSImageArgs
from zenml.core.components.data_gen.sources.interface import SourceInterface


# @beam.ptransform_fn
# @beam.typehints.with_input_types(beam.Pipeline)
# @beam.typehints.with_output_types(beam.typehints.Dict[Text, Any])
class ReadGCSBlobs(beam.DoFn):
    def __init__(self, service_account, *unused_args, **unused_kwargs):
        """This is the only way to not do crazy client instantiation cycles.

        Args:
            service_account:
            *unused_args:
            **unused_kwargs:
        """
        super().__init__(*unused_args, **unused_kwargs)
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

    def process(self, element, *args, **kwargs):
        """Parse the blob and download as bytestring

        Args:
            element:
            *args:
            **kwargs:
        """
        bucket_name, blob_name = self.parse_gcs_path(element)
        bucket = self.gcs_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob_as_bstring = blob.download_as_string()
        yield element, blob_as_bstring


@beam.ptransform_fn
@beam.typehints.with_input_types(beam.Pipeline)
@beam.typehints.with_output_types(beam.typehints.Dict[Text, Any])
def ReadFilesFromGCS(pipeline: beam.Pipeline,
                     source_args: Dict[Text, Any]) -> beam.pvalue.PCollection:
    """
    Args:
        pipeline (beam.Pipeline):
        source_args:
    """
    gcs_path = source_args['base_path']
    bucket_re = re.match('^gs://([^/]+)', gcs_path)
    bucket = bucket_re.group(1)
    if bucket_re is None:
        raise ValueError(
            'GCS base path must be in the form gs://<bucket>/.')

    sa = source_args['service_account']

    credentials = sa_service.Credentials.from_service_account_info(sa)
    client = storage.Client(project=sa["project_id"], credentials=credentials)

    blob_list = client.list_blobs(bucket_or_name=bucket)
    uri_list = list(os.path.join(gcs_path, blob.name) for blob in blob_list)

    files_and_contents = (pipeline
                          | beam.Create(uri_list)
                          | beam.ParDo(ReadGCSBlobs(sa))
                          | beam.Reshuffle()
                          | beam.Map(read_file_content, gcs_path)
                          )

    return files_and_contents


def read_file_content(path_and_file: Tuple[Text, bytes], gcs_path: Text):
    """
    Args:
        path_and_file:
        gcs_path (Text):
    """
    data_dict = {FILE_PATH: path_and_file[0],
                 BINARY_DATA: path_and_file[1],
                 BASE_PATH: gcs_path}

    base = os.path.basename(data_dict[FILE_PATH])
    data_dict[FILE_NAME] = os.path.splitext(base)[0]
    data_dict[FILE_EXT] = os.path.splitext(base)[1]

    return data_dict


class GCSImageSource(SourceInterface):
    ARG_KEYS = GCSImageArgs

    def beam_transform(self):
        return ReadFilesFromGCS
