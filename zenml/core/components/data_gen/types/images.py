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

import base64
import json
from typing import Dict, Text, Any

import apache_beam as beam
import numpy as np
import tensorflow as tf
from dateutil.parser import parse

from zenml.core.components.data_gen import constants
from zenml.core.components.data_gen.constants import BINARY_DATA, FILE_NAME, \
    BASE_PATH, FILE_PATH, FILE_EXT, METADATA, IMAGE, LABEL
from zenml.core.components.data_gen.constants import DestinationKeys
from zenml.core.components.data_gen.types.interface import TypeInterface
from zenml.core.components.data_gen.utils import init_bq_table, DtypeInferrer
from zenml.core.components.data_gen.utils import is_smaller_than


@beam.ptransform_fn
@beam.typehints.with_input_types(beam.typehints.Dict[Text, Any])
@beam.typehints.with_output_types(beam.pvalue.PDone)
def WriteImagesToBQ(datapoints: Dict[Text, Any],
                    schema: Dict[Text, Any],
                    destination: Dict[Text, Any]) -> beam.pvalue.PDone:
    """
    Args:
        datapoints:
        schema:
        destination:
    """
    allowed_ext = [".jpg", ".json", ".png", ".txt", ".jpeg"]

    images, label_file = (datapoints
                          | "FilterOutFiles" >> beam.Filter(lambda x:
                                                            x[FILE_EXT] in
                                                            allowed_ext)
                          | "SplitLabelFile" >> beam.Partition(SplitByFileName,
                                                               2))

    # label_file is actually a dict
    label_dict = beam.pvalue.AsSingleton(label_file)

    ready_images = (images
                    | "AddLabelAndMetadata" >> beam.Map(add_label_and_metadata,
                                                        label_dict)
                    | "AddTFExample" >> beam.Map(append_tf_example_to_image)
                    )

    # Obtain the schema
    if schema:
        schema_dict = schema
        assert all(v in ['STRING', 'INTEGER', 'FLOAT', 'BYTES']
                   for _, v in schema.items())
        init_bq_table(
            destination[DestinationKeys.PROJECT],
            destination[DestinationKeys.DATASET],
            destination[DestinationKeys.TABLE],
            schema)
    else:
        schema = (ready_images
                  | 'InferSchema' >> beam.CombineGlobally(
                    DtypeInferrer(),
                    project=destination[DestinationKeys.PROJECT],
                    dataset=destination[DestinationKeys.DATASET],
                    table=destination[DestinationKeys.TABLE]))

        schema_dict = beam.pvalue.AsSingleton(schema)

    # filter out data points larger than 10 MiB (default)
    final_images = (ready_images
                    | "FilterBySize" >> beam.Filter(is_smaller_than)
                    )

    result = (final_images
              | "WriteToBQ" >> beam.io.WriteToBigQuery(
                table=destination[DestinationKeys.TABLE],
                dataset=destination[DestinationKeys.DATASET],
                project=destination[DestinationKeys.PROJECT],
                write_disposition='WRITE_EMPTY',
                create_disposition="CREATE_NEVER")
              )

    return result


def _int64_feature(value):
    """Returns an int64_list from a bool / enum / int / uint.

    Args:
        value:
    """
    input_value = value.flatten() if (hasattr(value, 'shape') and
                                      (len(value.shape) > 1)) else [value]
    return tf.train.Feature(int64_list=tf.train.Int64List(value=input_value))


def _float_feature(value):
    """Returns an int64_list from a bool / enum / int / uint.

    Args:
        value:
    """
    input_value = value.flatten() if (hasattr(value, 'shape') and
                                      (len(value.shape) > 1)) else [value]
    return tf.train.Feature(float_list=tf.train.FloatList(
        value=input_value))


def _bytes_feature(value):
    """Returns a bytes_list from a string / byte.

    Args:
        value:
    """
    if isinstance(value, type(tf.constant(0))):
        value = value.numpy()
    return tf.train.Feature(bytes_list=tf.train.BytesList(value=[value]))


def _label_feature(value):
    """Returns an int64_list from a bool / enum / int / uint.

    Args:
        value:
    """
    # flatten first if it is a label array, which is the case e.g. in
    # computer vision + segmentation
    input_value = value.flatten() if (hasattr(value, 'shape') and
                                      (len(value.shape) > 1)) else [value]

    return tf.train.Feature(int64_list=tf.train.Int64List(
        value=input_value))


def _metadata_feature(metadata):
    # Returns all the metadata in the image as a string
    """
    Args:
        metadata:
    """
    metadata_as_bytes = str.encode(metadata)
    return tf.train.Feature(bytes_list=tf.train.BytesList(
        value=[metadata_as_bytes]))


def get_matching_label(label_data: Text, img_filename: Text):
    """
    Args:
        label_data (Text): Should be JSON-readable.
        img_filename (Text):

    Returns:
        * **label** (*Str, label key*)
        * **metadata** (*Dict, additional metadata information*)
    """

    # TODO: This can potentially go bad if the JSON is too big
    data_dict = json.loads(label_data)

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


def add_label_and_metadata(image_dict: Dict[Text, Any], label_dict: Text):
    """Parse a ByteString Image and convert to TFExample

    Args:
        image_dict:
        label_dict (Text):
    """
    filename = image_dict[FILE_NAME]

    label_data = label_dict[BINARY_DATA]
    label, metadata = get_matching_label(label_data, filename)

    image_dict[METADATA] = metadata
    image_dict[LABEL] = label

    return image_dict


def parse_metadata(metadata_dict: Dict[Text, Any]):
    """
    Args:
        metadata_dict:
    """
    key_feature_map = {
        "int": _int64_feature,
        "float": _float_feature,
        "str": _metadata_feature,
        "bytes": _bytes_feature}

    md_features = {}
    new_metadata = metadata_dict.copy()

    # separate check if value is list-like, also numpy.ndarray coercion
    for key, value in metadata_dict.items():
        val_type = type(value)
        if isinstance(value, list):
            value = np.array(value).flatten()
            val_type = type(value[0])

        # check whether a str is actually a timestamp,
        # important so that BQ does not throw an error
        if isinstance(value, str):
            try:
                ts = parse(value, fuzzy=True)
                ts = ts.strftime('%Y-%m-%dT%H:%M:%S.%f %Z')
                new_metadata[key] = ts
            except:
                pass

        md_features[key] = key_feature_map.get(val_type.__name__)(value)

    return new_metadata, md_features


def append_tf_example_to_image(image_dict: Dict[Text, Any]):
    # pop the binary data, base_path, metadata
    """
    Args:
        image_dict:
    """
    image_raw = image_dict.pop(BINARY_DATA)
    base_path = image_dict.pop(BASE_PATH)
    file_path = image_dict.pop(FILE_PATH)
    metadata_dict = image_dict.pop(METADATA)

    parsed_metadata, md_feature = parse_metadata(metadata_dict)
    # image = tf.io.decode_image(image_raw).numpy()
    # image_shape = image.shape

    feature = {
        # 'height': _int64_feature(image_shape[0]),
        # 'width': _int64_feature(image_shape[1]),
        # 'depth': _int64_feature(image_shape[2]),
        IMAGE: _bytes_feature(image_raw),
        LABEL: _label_feature(image_dict[LABEL]),
    }

    # update feature dict with metadata information
    feature.update(md_feature)
    # update image_dict with metadata info
    image_dict.update(parsed_metadata)

    tf_example = tf.train.Example(features=tf.train.Features(feature=feature))

    image_dict[constants.DATA_COL] = base64.b64encode(
        tf_example.SerializeToString())

    return image_dict


def SplitByFileName(element: Dict[Text, Any],
                    num_partitions: int) -> int:
    """
    Args:
        element:
        num_partitions (int):
    """
    try:
        # filename = element[FILE_NAME]
        file_ext = element[FILE_EXT]

        if file_ext.lower() in [".txt", ".json", ".csv"]:
            return 1
    # if we get a KeyError here, we are likely processing a BQ dict,
    # which should have the label already inside
    except KeyError:
        return 0

    return 0


class ImageConverter(TypeInterface):
    def convert(self):
        return WriteImagesToBQ
