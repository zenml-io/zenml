from __future__ import division

import io
import os
import struct
import typing
import warnings

import numpy as np
import torch
import torch.utils.data as data
from tensorflow.core.example import example_pb2


# The main solution for data ingestion is adapted
# from: https://github.com/vahidk/tfrecord


class TFRecordTorchDataset(data.IterableDataset):
    def __init__(self,
                 data_path: str,
                 index_path: typing.Union[str, None],
                 description: typing.Union[
                     typing.List[str], typing.Dict[str, str], None] = None,
                 shuffle_queue_size: typing.Optional[int] = None,
                 transform: typing.Callable[[dict], typing.Any] = None
                 ) -> None:
        super(TFRecordTorchDataset, self).__init__()
        self.data_path = data_path
        self.index_path = index_path
        self.description = description
        self.shuffle_queue_size = shuffle_queue_size
        self.transform = transform or (lambda x: x)

    def __iter__(self):
        worker_info = torch.utils.data.get_worker_info()
        if worker_info is not None:
            shard = worker_info.id, worker_info.num_workers
            np.random.seed(worker_info.seed % np.iinfo(np.uint32).max)
        else:
            shard = None
        it = tfrecord_loader(
            self.data_path, self.index_path, self.description, shard)
        if self.shuffle_queue_size:
            it = shuffle_iterator(it, self.shuffle_queue_size)
        if self.transform:
            it = map(self.transform, it)
        return it


def tfrecord_loader(data_path: str,
                    index_path: typing.Union[str, None],
                    description: typing.Union[
                        typing.List[str], typing.Dict[str, str], None] = None,
                    shard: typing.Optional[typing.Tuple[int, int]] = None,
                    ) -> typing.Iterable[typing.Dict[str, np.ndarray]]:
    typename_mapping = {
        "byte": "bytes_list",
        "float": "float_list",
        "int": "int64_list"
    }

    record_iterator = tfrecord_iterator(data_path, index_path, shard)

    for record in record_iterator:
        example = example_pb2.Example()
        example.ParseFromString(record)

        all_keys = list(example.features.feature.keys())
        if description is None:
            description = dict.fromkeys(all_keys, None)
        elif isinstance(description, list):
            description = dict.fromkeys(description, None)

        features = {}
        for key, typename in description.items():
            if key not in all_keys:
                raise KeyError(
                    f"Key {key} doesn't exist (select from {all_keys})!")
            # NOTE: We assume that each key in the example has only one field
            # (either "bytes_list", "float_list", or "int64_list")!
            field = example.features.feature[key].ListFields()[0]
            inferred_typename, value = field[0].name, field[1].value
            if typename is not None:
                tf_typename = typename_mapping[typename]
                if tf_typename != inferred_typename:
                    reversed_mapping = {v: k for k, v in
                                        typename_mapping.items()}
                    raise TypeError(
                        f"Incompatible type '{typename}' for `{key}` "
                        f"(should be '{reversed_mapping[inferred_typename]}').")

            # Decode raw bytes into respective data types
            if inferred_typename == "bytes_list":
                value = np.frombuffer(value[0], dtype=np.uint8)
            elif inferred_typename == "float_list":
                value = np.array(value, dtype=np.float32)
            elif inferred_typename == "int64_list":
                value = np.array(value, dtype=np.int32)
            features[key] = value

        yield features


def tfrecord_iterator(data_path: str,
                      index_path: typing.Optional[str] = None,
                      shard: typing.Optional[typing.Tuple[int, int]] = None
                      ) -> typing.Iterable[memoryview]:
    file = io.open(data_path, "rb")

    length_bytes = bytearray(8)
    crc_bytes = bytearray(4)
    datum_bytes = bytearray(1024 * 1024)

    def read_records(start_offset=None, end_offset=None):
        nonlocal length_bytes, crc_bytes, datum_bytes

        if start_offset is not None:
            file.seek(start_offset)
        if end_offset is None:
            end_offset = os.path.getsize(data_path)
        while file.tell() < end_offset:
            if file.readinto(length_bytes) != 8:
                raise RuntimeError("Failed to read the record size.")
            if file.readinto(crc_bytes) != 4:
                raise RuntimeError("Failed to read the start token.")
            length, = struct.unpack("<Q", length_bytes)
            if length > len(datum_bytes):
                datum_bytes = datum_bytes.zfill(int(length * 1.5))
            datum_bytes_view = memoryview(datum_bytes)[:length]
            if file.readinto(datum_bytes_view) != length:
                raise RuntimeError("Failed to read the record.")
            if file.readinto(crc_bytes) != 4:
                raise RuntimeError("Failed to read the end token.")
            yield datum_bytes_view

    if index_path is None:
        yield from read_records()
    else:
        index = np.loadtxt(index_path, dtype=np.int64)[:, 0]
        if shard is None:
            offset = np.random.choice(index)
            yield from read_records(offset)
            yield from read_records(0, offset)
        else:
            num_records = len(index)
            shard_idx, shard_count = shard
            start_index = (num_records * shard_idx) // shard_count
            end_index = (num_records * (shard_idx + 1)) // shard_count
            start_byte = index[start_index]
            end_byte = index[end_index] if end_index < num_records else None
            yield from read_records(start_byte, end_byte)

    file.close()


def cycle(iterator_fn: typing.Callable) -> typing.Iterable[typing.Any]:
    while True:
        for element in iterator_fn():
            yield element


def sample_iterators(iterators: typing.List[typing.Iterator],
                     ratios: typing.List[int]) -> typing.Iterable[typing.Any]:
    iterators = [cycle(iterator) for iterator in iterators]
    ratios = np.array(ratios)
    ratios = ratios / ratios.sum()
    while True:
        choice = np.random.choice(len(ratios), p=ratios)
        yield next(iterators[choice])


def shuffle_iterator(iterator: typing.Iterator,
                     queue_size: int) -> typing.Iterable[typing.Any]:
    buffer = []
    try:
        for _ in range(queue_size):
            buffer.append(next(iterator))
    except StopIteration:
        warnings.warn("Number of elements in the iterator is less than the "
                      f"queue size (N={queue_size}).")
    while buffer:
        index = np.random.randint(len(buffer))
        try:
            item = buffer[index]
            buffer[index] = next(iterator)
            yield item
        except StopIteration:
            yield buffer.pop(index)
