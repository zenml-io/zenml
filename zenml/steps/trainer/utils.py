import os

import pandas as pd
import tensorflow as tf

from zenml.utils import path_utils


def save_test_results(results, output_path):
    path_utils.create_dir_if_not_exists(output_path)
    output_path = os.path.join(output_path, 'test_results')
    with tf.io.TFRecordWriter(output_path) as writer:
        for example in to_serialized_examples(results):
            writer.write(example)

    return results


def to_serialized_examples(instance) -> tf.train.Example:
    example_list = []

    keys = list(instance.keys())
    size = instance[keys[0]].size

    for i in range(size):
        feature = {}
        for key in keys:
            value = instance[key][i]
            if value is None:
                raise Exception('The value can not possibly be None!')
            elif pd.api.types.is_integer_dtype(value):
                feature[key] = tf.train.Feature(
                    int64_list=tf.train.Int64List(value=[value]))
            elif pd.api.types.is_float_dtype(value):
                feature[key] = tf.train.Feature(
                    float_list=tf.train.FloatList(value=[value]))
            else:
                feature[key] = tf.train.Feature(
                    bytes_list=tf.train.BytesList(
                        value=list(map(tf.compat.as_bytes, [value]))))
        example_list.append(tf.train.Example(
            features=tf.train.Features(feature=feature)
        ).SerializeToString())

    return example_list
