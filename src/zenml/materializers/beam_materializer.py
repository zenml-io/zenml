# #  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
# import os
# from pathlib import Path
# from typing import Text, Tuple, Union
#
# import apache_beam as beam
#
# from zenml.logger import get_logger
# from zenml.materializers.base_materializer import BaseMaterializer
# from zenml.utils import path_utils
#
# logger = get_logger(__name__)
#
# DEFAULT_FILENAME = "data.csv"
#
#
# class BeamMaterializer(BaseMaterializer):
#     """Read/Write Apache Beam artifacts."""
#
#     TYPE_NAME = "beam"
#
#     def read_text(
#         self, pipeline, read_header=True
#     ) -> Union[beam.Pipeline, Tuple[str, beam.Pipeline]]:
#         """Appends a text reading step to an existing beam pipeline.
#
#         Args:
#             pipeline: The pipeline to which the reading step will be added.
#             read_header: Indicates if the header should be read and
#               returned in addition to the pipeline.
#
#         Returns:
#             If `read_header` is False, returns just the modified pipeline.
#             If `read_header` is True, returns the header as a comma-separated
#               string as well as the modified pipeline.
#         """
#         pipeline = pipeline | "ReadText" >> beam.io.ReadFromText(
#             file_pattern=os.path.join(self.artifact.uri, "*"),
#             skip_header_lines=True,
#         )
#
#         if read_header:
#             wildcard_qualifier = "*"
#             file_pattern = os.path.join(self.artifact.uri, wildcard_qualifier)
#
#             csv_files = path_utils.list_dir(self.artifact.uri)
#             if not csv_files:
#                 raise RuntimeError(
#                     "Split pattern {} does not match any files.".format(
#                         file_pattern
#                     )
#                 )
#
#             # weed out bad file exts with this logic
#             allowed_file_exts = [".csv", ".txt"]  # ".dat"
#             csv_files = [
#                 uri
#                 for uri in csv_files
#                 if Path(uri).suffix in allowed_file_exts
#             ]
#
#             logger.info(f"Matched {len(csv_files)}: {csv_files}")
#
#             # Always use header from file
#             logger.info(f"Using header from file: {csv_files[0]}.")
#             header = ",".join(path_utils.load_csv_header(csv_files[0]))
#
#             return header, pipeline
#         else:
#             return pipeline
#
#     def write_text(
#         self,
#         pipeline,
#         shard_name_template: Text = None,
#         header: Text = None,
#     ):
#         """Appends a text writing step to an existing beam pipeline.
#
#         Args:
#             pipeline: The pipeline to which the reading step will be added.
#             shard_name_template: A template string containing placeholders
#              for the shard number and shard count. See `beam.io.WriteToText`
#              for more information.
#             header: String to write at beginning of file as a header.
#         """
#         return pipeline | beam.io.WriteToText(
#             os.path.join(self.artifact.uri, DEFAULT_FILENAME),
#             shard_name_template=shard_name_template,
#             header=header,
#             num_shards=3,
#         )
