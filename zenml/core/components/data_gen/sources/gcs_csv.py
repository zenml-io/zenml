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
from typing import Text, Dict, Any
from uuid import uuid4
import oauth2client.service_account

import apache_beam as beam
from apache_beam.io.gcp import gcsio
from google.cloud import storage
from apache_beam.internal.http_client import get_new_http
from apache_beam.io.gcp.internal.clients.storage import StorageV1
from google.oauth2 import service_account as sa_service
from tfx.types.component_spec import ExecutionParameter
from tfx_bsl.coders import csv_decoder

from zenml.core.components.data_gen.sources.interface import SourceInterface


# @beam.ptransform_fn
# @beam.typehints.with_input_types(beam.Pipeline)
# @beam.typehints.with_output_types(beam.typehints.Dict[Text, Any])
class ProduceGCSBlobs(beam.DoFn):
    def __init__(self, service_account, *args, **kwargs):
        """This is the only way to not do crazy client instantiation cycles.

        Args:
            service_account:
            *args:
            **kwargs:
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
        sa = self._sa
        scope = "https://www.googleapis.com/auth/devstorage.read_only"
        self.credentials = oauth2client.service_account.\
            ServiceAccountCredentials.from_json_keyfile_dict(keyfile_dict=sa,
                                                             scopes=scope)
        self.gcs_client = StorageV1(credentials=self.credentials,
                                http=get_new_http(),
                                response_encoding="utf8")
        self.gcs_conn = gcsio.GcsIO(storage_client=self.gcs_client)

    def process(self, element, *args, **kwargs):
        """Parse the blob and download as bytestring

        Args:
            element:
            *args:
            **kwargs:
        """
        # bucket_name, blob_name = self.parse_gcs_path(element)
        # bucket = self.gcs_client.bucket(bucket_name)
        # blob = bucket.blob(blob_name)
        # blob_as_bstring = blob.download_as_string()
        # yield element, blob_as_bstring
        yield self.gcs_conn.open(element).read().decode("utf-8")


class CSVColumnInferrer(beam.DoFn):
    def __init__(self, service_account, max_header_size=16384, *unused_args,
                 **unused_kwargs):
        """Infer csv columns from the blob. Works for headers up to 16
        kilobytes.

        Args:
            service_account:
            max_header_size:
            *unused_args:
            **unused_kwargs:
        """
        super().__init__(*unused_args, **unused_kwargs)
        self._sa = service_account
        self.max_header_size = max_header_size

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
        """Parse the blob and download as bytestring.

        Args:
            element:
            *args:
            **kwargs:
        """
        bucket_name, blob_name = self.parse_gcs_path(element)
        bucket = self.gcs_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob_as_string = blob.download_as_string(start=0,
                                                 end=self.max_header_size
                                                 ).decode("utf8")

        first_row = blob_as_string.splitlines()[0]
        return first_row.strip().split(',')


def parse_columns(csv_file):
    """
    Args:
        csv_file:
    """
    return csv_file.readline().strip().split(',')


def create_bq_dict(line, column_names):
    """
    Args:
        line:
        column_names:
    """
    return dict(zip(column_names, line))


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
    client = storage.Client(credentials=credentials)

    blob_iter = client.list_blobs(bucket_or_name=bucket)
    blob_list = list(blob_iter)

    uri_list = list(os.path.join(gcs_path, blob.name) for blob in blob_list)

    allowed_file_exts = [".csv", ".txt"]  # ".dat"

    # weed out bad file exts with this logic
    csv_files = [uri for uri in uri_list if os.path.splitext(uri)[1]
                 in allowed_file_exts]

    if not csv_files:
        raise RuntimeError("Error: No files found with extensions {0}. "
                           "".format(allowed_file_exts))

    column_names = (pipeline
                    | "CreateCSVPColl" >> beam.Create(csv_files[:1])
                    | "InferColumns" >> beam.ParDo(
                CSVColumnInferrer(service_account=sa))
                    )

    colnames = beam.pvalue.AsList(column_names)
    # column_names = io_utils.load_csv_column_names(csv_files[0])
    # for csv_file in csv_files[1:]:
    #     if io_utils.load_csv_column_names(csv_file) != column_names:
    #         raise RuntimeError(
    #             'Files in same split {} have different header.'.format(
    #                 file_pattern))

    parsed_csv_lines = (
            pipeline
            | "CreateCSVs" >> beam.Create(csv_files)
            | "ReadCSVBlobs" >> beam.ParDo(ProduceGCSBlobs(service_account=sa))
            | 'ReadFromText' >> beam.io.ReadAllFromText(skip_header_lines=1)
            | 'ParseCSVLine' >> beam.ParDo(
        csv_decoder.ParseCSVLine(delimiter=','))
            | 'ExtractParsedCSVLines' >> beam.Map(create_bq_dict, colnames)
            )

    return parsed_csv_lines


class GCSCSVSource(SourceInterface):
    def get_config_spec(self):
        return {'base_path': ExecutionParameter(type=Text),
                'service_account': ExecutionParameter(type=Dict[Text, Any])}

    def config_parser(self, config):
        """
        Args:
            config:
        """
        return config

    def beam_transform(self):
        return ReadFilesFromGCS
