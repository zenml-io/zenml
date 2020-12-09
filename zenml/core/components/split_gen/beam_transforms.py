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

import bisect
import logging
import os
from typing import Dict, Text, Any, List

import apache_beam as beam
import tensorflow as tf
from google.cloud import bigquery

from zenml.core.components.split_gen import constants
from zenml.core.components.split_gen.utils import get_categorical_value
from zenml.core.components.split_gen.utils_legacy import map_cat_to_fold


class BigQueryConverter(object):
    """Helper class for bigquery result row to tf example conversion."""

    def __init__(self, bq_args):
        client = bigquery.Client(bq_args['project'])
        table_ref = client.dataset(bq_args['dataset']).table(bq_args['table'])
        table = client.get_table(table_ref)
        schema = table.schema
        self._type_map = {s.name: s.field_type for s in schema}

    def RowToExample(self, instance: Dict[Text, Any]) -> tf.train.Example:
        """Convert bigquery result row to tf example."""
        feature = {}
        for key, value in instance.items():
            # we can safely ignore row_number now
            if key == constants.DEFAULT_ROW_NUMBER:
                continue

            data_type = self._type_map[key]
            kwargs = {}
            if data_type == 'INTEGER':
                if value is not None:
                    kwargs = {'value': [value]}
                feature[key] = tf.train.Feature(
                    int64_list=tf.train.Int64List(**kwargs))
            elif data_type == 'FLOAT':
                if value is not None:
                    kwargs = {'value': [value]}
                feature[key] = tf.train.Feature(
                    float_list=tf.train.FloatList(**kwargs))
            elif data_type == 'STRING':
                if value is not None:
                    kwargs = {'value': [tf.compat.as_bytes(value)]}
                feature[key] = tf.train.Feature(
                    bytes_list=tf.train.BytesList(**kwargs))
            elif data_type == 'TIMESTAMP' or data_type == 'DATETIME':
                if value is not None:
                    kwargs = {'value': [tf.compat.as_bytes(str(value))]}
                feature[key] = tf.train.Feature(
                    bytes_list=tf.train.BytesList(**kwargs))
                pass
            elif data_type == 'BOOLEAN':
                if value is not None:
                    kwargs = {'value': [int(value)]}
                feature[key] = tf.train.Feature(
                    int64_list=tf.train.Int64List(**kwargs))
            else:
                raise RuntimeError(
                    'BigQuery column type {} is not supported.'.format(
                        data_type))
        return tf.train.Example(features=tf.train.Features(feature=feature))


class CatDictCombiner(beam.CombineFn):
    def create_accumulator(self, **kwargs) -> Dict[Text, int]:
        return dict()

    def add_input(self, accumulator: Dict[Text, int],
                  element: Dict[Text, int],
                  **kwargs,
                  ) -> Dict[Text, int]:
        k, v = element
        if k not in accumulator:
            accumulator[k] = v
        return accumulator

    def merge_accumulators(self,
                           accumulators: List[Dict[Text, int]],
                           **kwargs,
                           ) -> Dict[Text, int]:
        d = {}
        for acc in accumulators:
            for k, v in acc.items():
                if k not in d:
                    d[k] = v
        return d

    def extract_output(self,
                       accumulator: Dict[Text, Any],
                       **kwargs) -> Dict[Text, int]:
        accumulator["total"] = sum(accumulator.values())
        return accumulator


@beam.ptransform_fn
@beam.typehints.with_input_types(beam.Pipeline)
@beam.typehints.with_output_types(beam.typehints.Dict[Text, Any])
def ReadFromBigQuery(pipeline: beam.Pipeline,
                     query: Text,
                     exec_properties: Dict) -> beam.pvalue.PCollection:
    logging.info('Executing query: {}'.format(query))
    return (pipeline
            | 'QueryTable' >> beam.io.Read(
                beam.io.BigQuerySource(
                    project=exec_properties[constants.BQ_PROJECT],
                    query=query,
                    use_standard_sql=True)))


def SplitPartitionFn(element: tf.train.Example,
                     num_partitions: int,
                     exec_properties: Dict[Text, any],
                     category_map: Dict[Text, any],
                     limit_map: Dict[Text, any]) -> int:
    element_category = constants.DEFAULT_CATEGORY

    example, row_number = element

    # splitting by category (horizontal)
    if constants.CAT_COL in exec_properties:
        cat_col = exec_properties[constants.CAT_COL]

        element_category = get_categorical_value(example, cat_col=cat_col)
        # map_cat_to_fold returns the fold ID or -1, which is a placeholder
        # for "does not belong into any fold"
        fold_id = map_cat_to_fold(element_category, category_map)

        if exec_properties[constants.IDX_COL] is not None:
            if fold_id > 0:
                # fold_id > 0 <=> fold is eval or test, so return it,
                # otherwise split the train set further (hybrid split)
                return fold_id
        else:
            if fold_id >= 0:
                # return fold
                # TODO: What happens in the nosplit scenario?
                #  Does it even make sense to allow a categorical nosplit?
                return fold_id

    # move on to a hybrid split
    # hybrid splitting also happens implicitly when the element has a
    # CAT_COL feature category that was not selected into any of the folds.

    # splitting by row number (vertical)
    # element_row_number = element[constants.DEFAULT_ROW_NUMBER]

    # the row number limits for train, test, eval split by category
    row_num_limits = list(limit_map[element_category].values())

    # Python function to put row numbers into buckets
    return bisect.bisect(row_num_limits, row_number)


class CountExamples(beam.PTransform):
    def __init__(self):
        super(CountExamples, self).__init__()
        self._counter = 0

    def increase_count(self, element, *args, **kwargs):
        self._counter += 1
        return element, self._counter

    def expand(self, pcoll):
        return (pcoll
                | "CountExamples" >> beam.Map(self.increase_count))


@beam.ptransform_fn
@beam.typehints.with_input_types(bytes)
@beam.typehints.with_output_types(beam.pvalue.PDone)
def WriteSplit(example_split: beam.pvalue.PCollection,
               output_split_path: Text) -> beam.pvalue.PDone:
    """Shuffles and writes output split."""
    out_dir = os.path.join(output_split_path, 'data_tfrecord')
    logging.info('Writing output TFRecords to {}'.format(
        out_dir
    ))
    return (example_split
            | 'Write' >> beam.io.WriteToTFRecord(
                out_dir,
                file_name_suffix='.gz'))
