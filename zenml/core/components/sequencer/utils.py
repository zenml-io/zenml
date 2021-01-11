#  Copyright (c) maiot GmbH 2021. All Rights Reserved.
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


class ToDataframe(beam.DoFn):
    def process(self, element, *args, **kwargs):
        return [element.to_pandas()]


def df_to_example(instance) -> tf.train.Example:
    d = {col: instance[col] for col in instance.columns}

    feature = {}
    for key, value in d.items():
        if value is None:
            raise Exception('The value can not possibly be None!')
        elif value.dtype == int:
            data = value.tolist()
            feature[key] = tf.train.Feature(
                int64_list=tf.train.Int64List(value=data))
        elif value.dtype == float:
            data = value.tolist()
            feature[key] = tf.train.Feature(
                float_list=tf.train.FloatList(value=data))
        else:
            data = list(map(tf.compat.as_bytes, value.tolist()))
            feature[key] = tf.train.Feature(
                bytes_list=tf.train.BytesList(value=data))
    return tf.train.Example(features=tf.train.Features(feature=feature))


def serialize(instance):
    return instance.SerializeToString(deterministic=True)
