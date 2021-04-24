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
"""Image Datasource definition"""

import json
import os
from typing import Callable, Dict, Text, Any

import apache_beam as beam
from apache_beam.io import fileio

from zenml.components.data_gen.constants import BINARY_DATA, FILE_NAME, \
    FILE_EXT, METADATA, LABEL, IMAGE
from zenml.datasources import BaseDatasource
from zenml.utils.beam_utils import WriteToTFRecord


def read_file_content(file: beam.io.fileio.ReadableFile):
    """
    Read contents from a file handle in binary and return it along with some
    file metadata as a dict.

    Args:
        file (beam.io.fileio.ReadableFile): Beam ReadableFile object,
        corresponds to an image file read from disk.

    Returns:
        data_dict: Dict with binary data and file metadata.
    """
    file_path = file.metadata.path
    base = os.path.basename(file_path)

    data_dict = {BINARY_DATA: file.read(),
                 FILE_NAME: base,
                 FILE_EXT: os.path.splitext(base)[1]}

    return data_dict


def add_label_and_metadata(image_dict: Dict[Text, Any],
                           label_dict: Dict[Text, Any]):
    """
    Add label and metadata information to an image.

    Args:
        image_dict: Dict with image features.
        label_dict (Text): JSON-readable string with label information.

    Returns:
        image_dict: Updated image feature dict with label and metadata
         information.
    """
    filename = image_dict[FILE_NAME]

    label_data = label_dict[BINARY_DATA]
    label, metadata = get_matching_label(label_data, filename)

    image_dict.update(metadata)
    image_dict[LABEL] = label

    # pop binary image data and reinsert as "image"
    # for a more intuitive image feature name
    image_raw = image_dict.pop(BINARY_DATA)
    image_dict[IMAGE] = image_raw

    return image_dict


def get_matching_label(label_data: Text, img_filename: Text):
    """
    Get a label matching an image file name from a JSON-readable label file.

    Args:
        label_data (Text): Label string, needs to be JSON-readable.
        img_filename (Text): File name of the image.

    Returns:
        label: Label key of the image.
        metadata: Dict, additional metadata information.
    """

    # This can potentially go bad if the JSON is too big
    data_dict = json.loads(label_data)

    if img_filename not in data_dict:
        raise AssertionError(
            f'You need to provide a label for {img_filename} in your '
            f'labels.json!')
    img_data = data_dict[img_filename]

    if "label" not in img_data:
        raise ValueError("Error while parsing label file: No label "
                         "key was found. Make sure to specify your "
                         "image label under a \"label\" key.")

    label = img_data.pop(LABEL)

    try:
        metadata = img_data.pop(METADATA)
    except KeyError:
        metadata = {}

    # JSON parsing puts empty metadata dict as the empty string,
    # so in that case coerce to dict just to be type safe
    if not metadata:
        metadata = {}

    return label, metadata


@beam.typehints.with_input_types(Dict[Text, Any], int)
@beam.typehints.with_output_types(int)
def SplitByFileName(element: Dict[Text, Any],
                    num_partitions: int) -> int:
    """
    Helper function to identify the label file in a beam.Partition applied
    to the PCollection of input files.

    Args:
        element: Dict with image features.
        num_partitions (int): Number of partitions, unused.
    """
    filename = element[FILE_NAME]
    file_ext = element[FILE_EXT]

    if "label" in filename:
        return 1

    if file_ext.lower() in [".txt", ".json", ".csv"]:
        return 1

    return 0


class ImageDatasource(BaseDatasource):
    """ZenML Image datasource definition.

    Use this for image training pipelines.
    """

    def __init__(
            self,
            name: Text = None,
            base_path: Text = None,
            schema: Dict = None,
            **kwargs):
        """
        Create a Image datasource.

        Args:
            name (str): Name of datasource
            base_path (str): Path to folder of images
            schema (str): Optional schema for data to conform to.
        """
        self.base_path = base_path
        self.schema = schema
        super().__init__(name, base_path=base_path, schema=schema, **kwargs)

    def process(self, output_path: Text, make_beam_pipeline: Callable = None):
        wildcard_qualifier = "*"

        # ingest all the files from the base path by supplying the wildcard
        file_pattern = os.path.join(self.base_path, wildcard_qualifier)

        allowed_ext = [".jpg", ".json", ".png", ".txt", ".jpeg"]

        with make_beam_pipeline() as p:
            images, label_file = (
                    p
                    | fileio.MatchFiles(file_pattern)
                    | fileio.ReadMatches()
                    | beam.Map(read_file_content)
                    | "FilterOutFiles" >> beam.Filter(lambda x:
                                                      x[FILE_EXT] in
                                                      allowed_ext)
                    | "SplitLabelFile" >> beam.Partition(
                SplitByFileName,
                2))

            # label_file is actually a dict
            label_dict = beam.pvalue.AsSingleton(label_file)
            _ = (
                    images
                    | "AddLabelAndMetadata" >> beam.Map(add_label_and_metadata,
                                                        label_dict)
                    | WriteToTFRecord(self.schema, output_path))
