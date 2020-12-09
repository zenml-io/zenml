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

import time

from absl import logging

from datetime import datetime
from zenml.core.pipelines.config.standard_config import MethodKeys, DefaultKeys, GlobalKeys, EvaluatorKeys
import apache_beam as beam
import pytz
import tensorflow as tf

XF_SUFFIX = '_xf'


def parse_methods(input_dict, process, methods):
    """
    Args:
        input_dict:
        process:
        methods:
    """
    result = {}

    # Obtain the set of features
    f_set = set(input_dict.keys())
    f_list = list(sorted(f_set))

    for feature in f_list:
        assert isinstance(input_dict[feature], dict), \
            'Please specify a dict for every feature (empty dict if default)'

        # Check if the process for the given feature has been modified
        if process in input_dict[feature].keys():
            result[feature] = []
            for m in input_dict[feature][process]:
                MethodKeys.key_check(m)
                method_name = m[MethodKeys.METHOD]
                parameters = m[MethodKeys.PARAMETERS]
                # Check if the selected method exists and whether the
                # right parameters are given
                methods.check_name_and_params(method_name, parameters)
                result[feature].append(m)

    return result


def transformed_name(key):
    """
    Args:
        key:
    """
    return key + XF_SUFFIX


def timer(func):
    """
    Args:
        func:
    """

    def inner_func(*args, **kwargs):
        current_time = time.time()
        result = func(*args, **kwargs)
        logging.info("Function {} took {:.3f}s".format(
            func.__name__,
            time.time() - current_time
        ))
        return result

    return inner_func


def infer_schema(schema):
    """
    Args:
        schema:
    """
    schema_dict = dict()
    for feature, descriptions in schema.items():
        dtype = descriptions.dtype
        # These are ugly hacks for hard checking whether its broadly int, float
        #  bool or string.
        if dtype == float or 'float' in str(dtype):
            schema_dict[feature] = DefaultKeys.FLOAT
        elif dtype == int or 'int' in str(dtype):
            schema_dict[feature] = DefaultKeys.INTEGER
        elif dtype == bool or 'bool' in str(dtype):
            schema_dict[feature] = DefaultKeys.BOOLEAN
        elif dtype == str or 'string' in str(dtype):
            schema_dict[feature] = DefaultKeys.STRING
        else:
            raise AssertionError('Cannot infer schema dtype!')
    return schema_dict


def fill_defaults(config, default_config, schema):
    # Creating a feature spec for easier access
    """
    Args:
        config:
        default_config:
        schema:
    """
    for feature, descriptions in config.items():
        if len(descriptions) == 0:
            config[feature] = default_config[schema[feature]]
    return config


def get_function_dict(config, methods):
    """
    Args:
        config:
        methods:
    """
    result = dict()
    for feature, descriptions in config.items():
        result[feature] = []
        for d in descriptions:
            method = d[MethodKeys.METHOD]
            params = d[MethodKeys.PARAMETERS]

            result[feature].append(methods.get_method(method)(**params))

    return result


def build_eval_config(config, use_defaults=False):
    """
    Args:
        config:
        use_defaults:
    """
    import tensorflow_model_analysis as tfma
    from google.protobuf.wrappers_pb2 import BoolValue

    # SLICING SPEC
    slicing_specs = [tfma.SlicingSpec()]
    evaluator_config = config[GlobalKeys.EVALUATOR]

    if EvaluatorKeys.SLICES_ in evaluator_config:
        slices_config = evaluator_config[EvaluatorKeys.SLICES_]
        slicing_specs.extend([tfma.SlicingSpec(feature_keys=e)
                              for e in slices_config])

    # MODEL SPEC
    labels = sorted(list(config[GlobalKeys.LABELS].keys()))
    if len(labels) > 1:
        model_specs = [tfma.ModelSpec(
            signature_name='ce_eval',
            label_keys={'output_{}'.format(i + 1): 'label_{}_xf'.format(l)
                        for i, l in enumerate(labels)})]
    else:
        model_specs = [tfma.ModelSpec(
            signature_name='ce_eval',
            label_key='label_{}_xf'.format(labels[0]))]

    # METRIC SPEC
    baseline = [tfma.MetricConfig(class_name='ExampleCount')]

    if EvaluatorKeys.METRICS_ in evaluator_config:
        metrics_config = evaluator_config[EvaluatorKeys.METRICS_]

        if isinstance(metrics_config, dict):
            metric_keys = sorted(list(metrics_config.keys()))
            assert metric_keys == labels, \
                'The keys within the metrics {} should match the keys ' \
                'within the labels key {}'.format(metric_keys, labels)

            metrics_specs = []
            for i, key in metric_keys:
                metrics = baseline.copy()
                metrics.extend([
                    tfma.MetricConfig(class_name=to_camel_case(m))
                    for m in metrics_config[key]])

                metrics_specs.append(
                    tfma.MetricsSpec(
                        output_names=['output_{}'.format(i + 1)],
                        metrics=metrics))

        elif isinstance(metrics_config, list):
            metrics = baseline.copy()

            metrics.extend([tfma.MetricConfig(class_name=to_camel_case(m))
                            for m in metrics_config])

            metrics_specs = [tfma.MetricsSpec(metrics=metrics)]

        else:
            raise ValueError('Metrics should either be a list (single-output) '
                             'or a dict (multi-output).')
    else:
        metrics_specs = [tfma.MetricsSpec(metrics=baseline)]

    return tfma.EvalConfig(
        model_specs=model_specs,
        slicing_specs=slicing_specs,
        metrics_specs=metrics_specs,
        options=tfma.Options(
            include_default_metrics=BoolValue(value=use_defaults)))


def to_camel_case(s):
    """
    Args:
        s:
    """
    return ''.join(list(map(lambda x: x.capitalize(), s.split('_'))))


def convert_datetime_to_secs(dt):
    """
    Args:
        dt:
    """
    delta = dt - datetime(year=1970, month=1, day=1, tzinfo=pytz.utc)
    return int(delta.total_seconds())


def df_to_example(instance) -> tf.train.Example:
    """
    Args:
        instance:
    """
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


class ArrowToDataframe(beam.DoFn):
    def process(self, element, *args, **kwargs):
        """
        Args:
            element:
            *args:
            **kwargs:
        """
        return [element.to_pandas()]
