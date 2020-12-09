# #  Copyright (c) maiot GmbH 2020. All Rights Reserved.
# #
# #  Licensed under the Apache License, Version 2.0 (the "License");
# #  you may not use this file except in compliance with the License.
# #  You may obtain a copy of the License at:
# #
# #       http://www.apache.org/licenses/LICENSE-2.0
# #
# #  Unless required by applicable law or agreed to in writing, software
# #  distributed under the License is distributed on an "AS IS" BASIS,
# #  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# #  or implied. See the License for the specific language governing
# #  permissions and limitations under the License.
#
# from typing import Text, Dict, Any
#
# import apache_beam as beam
# import oauth2client.service_account
# from apache_beam.internal.http_client import get_new_http
# from apache_beam.io.gcp import bigquery_tools
# from apache_beam.io.gcp.internal.clients.bigquery import BigqueryV2
#
# from zenml.core.components.data_gen.constants import BQArgs
# from zenml.core.components.data_gen.sources.interface import SourceInterface
#
#
# class CEBigQuerySource(beam.io.BigQuerySource):
#     def __init__(self, credentials, *args, **kwargs):
#         """
#         Args:
#             credentials:
#             *args:
#             **kwargs:
#         """
#         super(CEBigQuerySource, self).__init__(*args, **kwargs)
#         # self.bq_client = bq_client
#         self.credentials = credentials
#         self.bq_client = BigqueryV2(
#             http=get_new_http(),
#             credentials=self.credentials,
#             response_encoding='utf8')
#
#     def reader(self, *args, **kwargs):
#         """
#         Args:
#             *args:
#             **kwargs:
#         """
#         return bigquery_tools.BigQueryReader(
#             source=self,
#             test_bigquery_client=self.bq_client,
#             use_legacy_sql=self.use_legacy_sql,
#             flatten_results=self.flatten_results,
#             kms_key=self.kms_key)
#
#
# @beam.ptransform_fn
# @beam.typehints.with_input_types(beam.Pipeline)
# @beam.typehints.with_output_types(beam.typehints.Dict[Text, Any])
# def ReadFromBigQuery(pipeline: beam.Pipeline,
#                      source_args: Dict[Text, Any]) -> beam.pvalue.PCollection:
#     """
#     Args:
#         pipeline (beam.Pipeline):
#         source_args:
#     """
#     query = '''SELECT * FROM `{project}.{dataset}.{table}`'''.format(
#         project=source_args[BQArgs.PROJECT],
#         dataset=source_args[BQArgs.DATASET],
#         table=source_args[BQArgs.TABLE])
#
#     if BQArgs.LIMIT_ in source_args:
#         query += 'LIMIT {}'.format(source_args[BQArgs.LIMIT_])
#
#     if BQArgs.SERVICE_ACCOUNT_ in source_args:
#         # Its a private dataset
#         sa = source_args[BQArgs.SERVICE_ACCOUNT_]
#         scope = "https://www.googleapis.com/auth/bigquery"
#         credentials = oauth2client.service_account.ServiceAccountCredentials. \
#             from_json_keyfile_dict(keyfile_dict=sa,
#                                    scopes=scope)
#         bq_source = CEBigQuerySource(
#             # bq_client=bq_client,
#             credentials=credentials,
#             project=source_args[BQArgs.PROJECT],
#             query=query,
#             use_standard_sql=True)
#
#     else:  # we have a public table, no special permissions needed
#         bq_source = beam.io.BigQuerySource(
#             project=source_args[BQArgs.PROJECT],
#             query=query,
#             use_standard_sql=True)
#
#     return (pipeline
#             | 'QueryTable' >> beam.io.Read(source=bq_source))
#
#
# class BigQuerySource(SourceInterface):
#     ARG_KEYS = BQArgs
#
#     def beam_transform(self):
#         return ReadFromBigQuery
