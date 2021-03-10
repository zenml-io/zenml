from __future__ import division

import os
from abc import ABC
from itertools import starmap

import numpy as np
import pandas as pd
import tensorflow as tf
import torch
import torch.utils.data as data
from tensorflow.python.data.ops import dataset_ops
from tensorflow.python.data.ops import readers as core_readers
from tensorflow.python.framework import dtypes


class TFRecordTorchDataset(data.IterableDataset, ABC):
    def __init__(self,
                 file_pattern,
                 spec) -> None:
        super(TFRecordTorchDataset, self).__init__()

        self.dataset = create_tf_dataset(file_pattern=file_pattern,
                                         spec=spec)

    def __iter__(self):
        it = _create_iterator(self.dataset)
        it = _shuffle_iterator(it, 12)
        return it


def _create_iterator(dataset):
    iterator = dataset.as_numpy_iterator()
    iterator = starmap(_convert_to_tensors, iterator)
    return iterator


def _convert_to_tensors(features, label, raw):
    return {k: torch.from_numpy(v) for k, v in features.items()}, \
           {k: torch.from_numpy(v) for k, v in label.items()}, \
           raw


def _shuffle_iterator(iterator,
                      queue_size: int):
    buffer = []
    try:
        for _ in range(queue_size):
            buffer.append(next(iterator))
    except StopIteration:
        raise Exception('Iteration stopped!')
    while buffer:
        index = np.random.randint(len(buffer))
        try:
            item = buffer[index]
            buffer[index] = next(iterator)
            yield item
        except StopIteration:
            yield buffer.pop(index)


def _gzip_reader_fn(filenames):
    """
    Small utility returning a record reader that can read gzipped files.

    Args:
        filenames: Names of the compressed TFRecord data files.
    """
    return tf.data.TFRecordDataset(filenames, compression_type='GZIP')


def _split_inputs_labels(x):
    inputs = {}
    labels = {}
    raw = {}
    for e in x:
        if e.startswith('label'):
            labels[e[len('label_'):-len('_xf')]] = x[e]
        elif e.endswith('_xf'):
            inputs[e[:-len('_xf')]] = x[e]
        else:
            raw[e] = x[e]

    return inputs, labels, raw


def create_tf_dataset(file_pattern,
                      spec,
                      num_epochs=1,
                      shuffle=False,
                      shuffle_seed=None,
                      shuffle_buffer_size=None,
                      reader_num_threads=None,
                      parser_num_threads=None,
                      prefetch_buffer_size=None):
    reader = _gzip_reader_fn

    if reader_num_threads is None:
        reader_num_threads = 1
    if parser_num_threads is None:
        parser_num_threads = 2
    if prefetch_buffer_size is None:
        prefetch_buffer_size = dataset_ops.AUTOTUNE

    # Create dataset of all matching filenames
    dataset = dataset_ops.Dataset.list_files(file_pattern=file_pattern,
                                             shuffle=shuffle,
                                             seed=shuffle_seed)

    if reader_num_threads == dataset_ops.AUTOTUNE:
        dataset = dataset.interleave(
            lambda filename: reader(filename),
            num_parallel_calls=reader_num_threads)
        options = dataset_ops.Options()
        options.experimental_deterministic = True
        dataset = dataset.with_options(options)
    else:
        def apply_fn(dataset):
            return core_readers.ParallelInterleaveDataset(
                dataset,
                lambda filename: reader(filename),
                cycle_length=reader_num_threads,
                block_length=1,
                sloppy=True,
                buffer_output_elements=None,
                prefetch_input_elements=None)

        dataset = dataset.apply(apply_fn)

    if dataset_ops.get_legacy_output_types(dataset) == (dtypes.string,
                                                        dtypes.string):
        dataset = dataset_ops.MapDataset(dataset,
                                         lambda _, v: v,
                                         use_inter_op_parallelism=False)

    if shuffle:
        dataset = dataset.shuffle(shuffle_buffer_size, shuffle_seed)
    if num_epochs != 1:
        dataset = dataset.repeat(num_epochs)

    dataset = dataset.map(lambda x: tf.io.parse_example(x, spec))
    dataset = dataset.map(_split_inputs_labels)
    dataset = dataset.prefetch(prefetch_buffer_size)
    return dataset


def combine_batch_results(x):
    """

    :param x: list of batches, batches are dicts where keys are features and
    values are the values within the back
    :return:
    """
    result = {}
    for batch in x:
        for feature, values in batch.items():
            if isinstance(values, torch.Tensor):
                values = torch.squeeze(values).detach().numpy()

            if feature not in result:
                result[feature] = values

            else:
                result[feature] = np.concatenate((result[feature],
                                                  values), axis=0)

    return result


def save_test_results(results, output_path):
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
