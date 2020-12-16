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

import apache_beam as beam
import tensorflow as tf
import json
import numpy as np
import base64
from typing import Dict, Text, Any, Tuple
from dateutil.parser import parse

from zenml.core.components.data_gen import constants
from zenml.core.components.data_gen.constants import BINARY_DATA, FILE_NAME, \
    BASE_PATH, FILE_PATH, FILE_EXT, METADATA, IMAGE, MASK
from zenml.core.components.data_gen.constants import DestinationKeys
from zenml.core.components.data_gen.types.interface import TypeInterface
from zenml.core.components.data_gen.utils import init_bq_table, DtypeInferrer
from zenml.core.components.data_gen.utils import is_smaller_than


@beam.ptransform_fn
@beam.typehints.with_input_types(beam.typehints.Dict[Text, Any])
@beam.typehints.with_output_types(beam.pvalue.PDone)
def WriteCVImagesToBQ(datapoints: Dict[Text, Any],
                      schema: Dict[Text, Any],
                      destination: Dict[Text, Any]) \
        -> beam.pvalue.PDone:
    """
    Args:
        datapoints:
        schema:
        destination:
    """
    allowed_ext = [".jpg", ".json", ".png", ".txt", ".jpeg"]

    cv_data = (datapoints
               | "FilterOutFiles" >> beam.Filter(lambda x:
                                                 x[FILE_EXT]
                                                 in allowed_ext)
               | "ConvertToNamedTuple" >> beam.Map(lambda x:
                                                   (x[FILE_NAME], x))
               | "CombineByName" >> beam.GroupByKey()
               # now we have a list of inputs grouped by file name URI
               # add and parse metadata, create TFExample
               | "AddTFExandMD" >> beam.Map(append_tf_example_to_image)
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
        schema = (cv_data
                  | 'InferSchema' >> beam.CombineGlobally(
                    DtypeInferrer(),
                    project=destination[DestinationKeys.PROJECT],
                    dataset=destination[DestinationKeys.DATASET],
                    table=destination[DestinationKeys.TABLE]))

        schema_dict = beam.pvalue.AsSingleton(schema)

    # filter out data points larger than 10 MiB (default)
    final_images = (cv_data
                    | "FilterBySize" >> beam.Filter(is_smaller_than)
                    )

    # TODO: For my dummy dataset, this fails with
    #  BrokenPipeError: [Errno 32] Broken pipe.
    #  SO hints at a possible row / request size error
    #  because the rows may be too big. More info:
    #  https://stackoverflow.com/questions/59856658/google-bigquery-payload
    #  -size-limit-of-10485760-bytes
    #  https://cloud.google.com/bigquery/quotas
    result = (final_images
              | "WriteToBQ" >> beam.io.WriteToBigQuery(
                table=destination[DestinationKeys.TABLE],
                dataset=destination[DestinationKeys.DATASET],
                project=destination[DestinationKeys.PROJECT],
                create_disposition="CREATE_NEVER",
                write_disposition='WRITE_EMPTY')
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


def get_metadata(label_data: Text, img_filename: Text) -> Dict[Text, Any]:
    """
    Args:
        label_data (Text): Should be JSON-readable.
        img_filename (Text):

    Returns:
        Dict, additional metadata information: **metadata**
    """

    # TODO: This can potentially go bad if the JSON is too big
    data_dict = json.loads(label_data)

    try:
        metadata = data_dict.pop(METADATA)
    except KeyError:
        metadata = {}

    # JSON parsing puts empty metadata dict as the empty string,
    # so in that case coerce to dict just to be type safe
    if not metadata:
        metadata = {}

    return metadata


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
    new_metadata = metadata_dict.copy()  # copy of the data

    # separate check if value is list-like, also numpy.ndarray coercion
    for key, value in metadata_dict.items():
        val_type = type(value)
        if isinstance(value, list):
            value = np.array(value).flatten()
            val_type = type(value[0])

        # check whether a str is actually a timestamp
        if isinstance(value, str):
            try:
                ts = parse(value, fuzzy=True)
                ts = ts.strftime('%Y-%m-%dT%H:%M:%S.%f %Z')
                new_metadata[key] = ts
            except:
                pass

        try:
            md_features[key] = key_feature_map.get(val_type.__name__)(value)
        except KeyError:
            raise RuntimeError("Error: Unrecognized data type in TFExample "
                               "construction.")

    return new_metadata, md_features


def append_tf_example_to_image(data_tuple: Tuple[Text, Dict[Text, Any]]):
    """This function breaks down images, masks and metadata into a single dict
    that can be pushed into BigQuery.

    Args:
        data_tuple:

    Returns:
        Dict, with proper types, formatting ready for BQ insertion: **image_dict**
    """
    image_dict = {}
    feature = {}

    data_list = data_tuple[-1]
    # TODO: Check length of data_list to infer whether a label, image or
    #  mask is missing; proceed accordingly

    for data_dict in data_list:
        raw_data = data_dict.pop(BINARY_DATA)
        base_path = data_dict.pop(BASE_PATH)
        file_path = data_dict.pop(FILE_PATH)

        # image path, data is image data
        if "image" in file_path:
            image = tf.io.decode_image(raw_data).numpy()
            image_shape = image.shape

            feature.update({'height': _int64_feature(image_shape[0]),
                            'width': _int64_feature(image_shape[1]),
                            'depth': _int64_feature(image_shape[2]),
                            IMAGE: _bytes_feature(raw_data)})

        elif "mask" in file_path:
            mask = tf.io.decode_image(raw_data).numpy()
            mask_shape = mask.shape
            feature.update({'mask_height': _int64_feature(mask_shape[0]),
                            'mask_width': _int64_feature(mask_shape[1]),
                            'mask_depth': _int64_feature(mask_shape[2]),
                            MASK: _bytes_feature(raw_data)})

        elif "metadata" in file_path:
            metadata = get_metadata(raw_data, data_dict[FILE_NAME])
            parsed_metadata, md_feature = parse_metadata(metadata)
            # update feature dict with metadata information
            image_dict.update(parsed_metadata)
            feature.update(md_feature)

        else:
            continue

    tf_example = tf.train.Example(features=tf.train.Features(feature=feature))

    image_dict[constants.DATA_COL] = base64.b64encode(
        tf_example.SerializeToString())

    return image_dict


class CVImageConverter(TypeInterface):
    def convert(self):
        return WriteCVImagesToBQ
