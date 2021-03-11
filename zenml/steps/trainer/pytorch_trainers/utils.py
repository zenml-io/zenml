from __future__ import division

from abc import ABC
from itertools import starmap

import numpy as np
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
        xf_feature_spec = {x: spec[x] for x in spec if x.endswith('_xf')}

        self.dataset = create_tf_dataset(file_pattern=file_pattern,
                                         spec=xf_feature_spec)

    def __iter__(self):
        it = _create_iterator(self.dataset)
        it = _shuffle_iterator(it, 12)
        return it


def _create_iterator(dataset):
    iterator = dataset.as_numpy_iterator()
    iterator = starmap(_convert_to_tensors, iterator)
    return iterator


def _convert_to_tensors(features, label):
    return torch.FloatTensor(list(features.values())).squeeze(dim=-1), \
           torch.FloatTensor(list(label.values())).squeeze(dim=-1)


def _shuffle_iterator(iterator,
                      queue_size: int):
    buffer = []
    try:
        for _ in range(queue_size):
            buffer.append(next(iterator))
    except StopIteration:
        raise Exception('asdf')
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
    for e in x:
        if not e.startswith('label'):
            inputs[e[:-len('_xf')]] = x[e]
        else:
            labels[e[len('label_'):-len('_xf')]] = x[e]

    return inputs, labels


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
