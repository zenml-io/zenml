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

import math
import os
from math import isclose
from typing import List, Text, Dict, Any

import tensorflow as tf
import tensorflow_data_validation as tfdv
from tensorflow_data_validation.types import FeaturePath
from tensorflow_data_validation.utils import stats_util
from tfx import types
from tfx.components.schema_gen.executor import _DEFAULT_FILE_NAME, SCHEMA_KEY
from tfx.types import artifact_utils
from tfx.types.artifact import Artifact
from tfx.utils import io_utils

from zenml.core.components.split_gen import constants


def infer_split_names(exec_properties):
    """
    Small function to infer the split names from a dict passed to the TFX
    component executor.
    """
    # TODO: Hardcoded folds :( later: folds = exec_properties[
    #  constants.SPLIT_NAMES] or something
    cat_options = [constants.CAT_TRAIN, constants.CAT_EVAL, constants.CAT_TEST,
                   constants.CAT_NOSPLIT]
    c_ratio_options = [constants.C_RATIO_TRAIN, constants.C_RATIO_EVAL,
                       constants.C_RATIO_TEST, constants.C_RATIO_NOSPLIT]
    idx_options = [constants.I_RATIO_TRAIN, constants.I_RATIO_EVAL,
                   constants.I_RATIO_TEST, constants.I_RATIO_NOSPLIT]
    names = [constants.TRAIN, constants.EVAL, constants.TEST,
             constants.NOSPLIT]

    # rather obscure dict construction to map cat and idx constants to the
    # split names (workloads)
    map_dict = dict(zip(cat_options + idx_options + c_ratio_options,
                        names + names + names))

    split_names = []
    if not any(exec_properties[opt] is not None
               for opt in cat_options + c_ratio_options):
        # separate check! categorical and index can exist independently
        if not any(exec_properties[opt] is not None for opt in idx_options):
            # "naked config", corresponds to nosplit
            split_names.append(constants.NOSPLIT)
            return split_names
        else:
            # pick up all the split folds from the idx portion
            for opt in idx_options:
                if exec_properties[opt] is not None:
                    split_names.append(map_dict[opt])
            return split_names

    else:
        for opt in cat_options:
            if exec_properties[opt] is not None:
                split_names.append(map_dict[opt])

        for opt in c_ratio_options:
            if exec_properties[opt] is not None:
                split_names.append(map_dict[opt])
        # Here we assume that categorical and index ratio dicts are consistent,
        # i.e. have the same keys and workload (train-eval, nosplit etc.)
        return split_names


def construct_limit_map(cat_len_map: Dict[Text, int],
                        category_map: Dict[Text, List[Text]],
                        index_split: Dict[Text, float]):
    folds = [constants.TRAIN, constants.EVAL,
             constants.TEST, constants.NOSPLIT]
    limit_map = {}

    for i, cat_list in enumerate(category_map.values()):
        for cat in cat_list:
            limit_map[cat] = dict(zip(folds[:i], [-math.inf] * i))

    for k, v in cat_len_map.items():
        if k in limit_map:
            continue

        ratio = 0
        limit_dict = {}
        for fold, index_ratio in index_split.items():
            ratio += index_ratio

            if not isclose(ratio, 1.0):
                limit_dict[fold] = v * ratio

        limit_map[k] = limit_dict

    return limit_map


def parse_statistics(split_name: Text,
                     statistics: List[Artifact]) -> Dict[Text, int]:
    stats_uri = io_utils.get_only_uri_in_dir(
        artifact_utils.get_split_uri(statistics, split_name))

    stats = tfdv.load_statistics(stats_uri)

    return stats


def parse_schema(input_dict: Dict[Text, List[types.Artifact]]):
    schema = input_dict.get(SCHEMA_KEY, None)
    if not schema:
        return schema
    else:
        schema_path = os.path.join(
            artifact_utils.get_single_uri(schema),
            _DEFAULT_FILE_NAME)
        schema_reader = io_utils.SchemaReader()
        parsed_schema = schema_reader.read(schema_path)

        return parsed_schema


def parse_cat_len_map(statistics,
                      category_column: Text):
    feature_stats = stats_util.get_feature_stats(statistics.datasets[0],
                                                 FeaturePath(
                                                     [category_column]))
    if not hasattr(feature_stats, 'string_stats'):
        # this is a problem
        raise AssertionError(
            "You can only do horizontal splits on categorical variables")

    category_map = {}
    for v in feature_stats.string_stats.top_values:
        key = v.value
        n = v.frequency
        category_map[key] = n

    return category_map


def get_index_split(split_names, exec_properties) -> Dict[Text, float]:
    index_split = dict()
    # converter for fold keys to index ratio fold keys
    idx_ratio_converter = {constants.TRAIN: constants.I_RATIO_TRAIN,
                           constants.EVAL: constants.I_RATIO_EVAL,
                           constants.TEST: constants.I_RATIO_TEST,
                           constants.NOSPLIT: constants.I_RATIO_NOSPLIT}

    for name in split_names:
        converted_name = idx_ratio_converter[name]
        if exec_properties[converted_name]:
            index_split[name] = exec_properties[converted_name]

    return index_split


def get_category_map(schema, exec_properties):
    """
    Helper to infer the categories at executor runtime, either from the
    plaintext entries in the CAT_xyz entries or from the C_RATIO_xyz entries
    in the exec_properties.
    """

    mapped_dict = {}

    c_ratio_keys = [constants.C_RATIO_TRAIN, constants.C_RATIO_EVAL,
                    constants.C_RATIO_TEST, constants.C_RATIO_NOSPLIT]

    cat_keys = [constants.CAT_TRAIN, constants.CAT_EVAL,
                constants.CAT_TEST, constants.CAT_NOSPLIT]

    if any(exec_properties[key] is not None for key in c_ratio_keys):
        # extract categorical column
        cat_col = exec_properties[constants.CAT_COL]

        # infer categories by dummy BQ query
        categories = sorted(get_possible_categories(schema, cat_col))

        c_ratio = {key: exec_properties[key] for key in c_ratio_keys
                   if exec_properties[key] is not None}

        # partition the category list with the ratio in the executor spec
        cat_dict = partition_cat_list(categories, c_ratio)

        # map fold keys to category dict keys
        cat_converter = dict(zip(c_ratio_keys, cat_keys))

        mapped_dict = {cat_converter[k]: v for k, v in cat_dict.items()}

    if any(exec_properties[key] is not None for key in cat_keys):
        # exec_properties are concatenated lists of categories with comma as
        # separator -> split them by the "," inside
        cat_col = exec_properties[constants.CAT_COL]

        cat_dict = {key: exec_properties[key].split(",") for key in cat_keys
                    if exec_properties[key] is not None}

        mapped_dict = cat_dict

    return mapped_dict


def partition_cat_list(cat_list: List[Text], c_ratio: Dict[Text, Any]):
    """
    Helper to split a category list by the entries in a category split dict.
    Scales well in the number of folds
    """
    cat_dict = {}

    num_cats = len(cat_list)
    ratio = 0

    # This might produce unexpected results if the number of categories
    # is lower than the number of folds.
    for fold, fold_pct in c_ratio.items():
        left_bound = round(num_cats * ratio)
        ratio += fold_pct
        right_bound = round(num_cats * ratio)
        # write categories for fold to the cat_list dict
        cat_dict[fold] = cat_list[left_bound:right_bound]

    return cat_dict


def get_possible_categories(schema, cat_col: Text):
    category_domain = tfdv.get_domain(schema, cat_col)

    # get category list from result proto
    value_list = list(category_domain.value)

    return value_list


def get_categorical_value(example: tf.train.Example, cat_col: Text):
    cat_feature = example.features.feature[cat_col]

    possible_types = ["bytes", "float", "int64"]

    for datatype in possible_types:
        value_list = getattr(cat_feature, datatype + "_list")

        if value_list.value:
            value = value_list.value[0]
            if hasattr(value, "decode"):
                return value.decode()
            else:
                return value

    # TODO: Should we raise here? This could happen in a NULL type situation
    return None
