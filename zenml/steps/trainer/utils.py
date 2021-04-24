import os

import numpy as np
import pandas as pd
import tensorflow as tf

from zenml.utils import path_utils

SPLIT_MAPPING = 'split_mapping'

TRAIN_SPLITS = 'train_splits'
EVAL_SPLITS = 'eval_splits'
TEST_SPLITS = 'test_splits'


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
    num_samples = instance[keys[0]].shape[0]

    for i in range(num_samples):
        feature = {}
        for key in keys:
            value = instance[key][i]

            if value is None:
                raise Exception('The value can not possibly be None!')

            if len(value.shape) < 1:
                value = np.array([value])

            if pd.api.types.is_integer_dtype(value):
                feature[key] = tf.train.Feature(
                    int64_list=tf.train.Int64List(value=value))
            elif pd.api.types.is_float_dtype(value):
                feature[key] = tf.train.Feature(
                    float_list=tf.train.FloatList(value=value))
            else:
                vec_F = np.vectorize(tf.compat.as_bytes)
                feature[key] = tf.train.Feature(
                    bytes_list=tf.train.BytesList(value=vec_F(value)))
        example_list.append(tf.train.Example(
            features=tf.train.Features(feature=feature)
        ).SerializeToString())

    return example_list


def combine_batch_results(x):
    import torch

    result = {}
    for batch in x:
        for feature, values in batch.items():
            if isinstance(values, torch.Tensor):
                temp = torch.squeeze(values).detach().numpy()
                values = np.reshape(temp, values.size())
            elif isinstance(values, tf.Tensor):
                values = values.numpy()

            if feature not in result:
                result[feature] = values
            else:
                result[feature] = np.concatenate((result[feature],
                                                  values), axis=0)

    return result
