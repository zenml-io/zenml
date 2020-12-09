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

import json
import os
from math import isclose
from typing import List, Text, Dict, Any

import absl
from google.cloud import bigquery

from zenml.core.components.data_gen.constants import DATA_COL
from zenml.core.components.split_gen import constants
from zenml.core.pipelines.config.standard_config import SplitKeys, GlobalKeys
from zenml.utils.constants import ZENML_PIPELINE_CONFIG


def check_split_ratio_sum(split_ratio_dict: Dict[Text, Any]):
    # using round because of float inaccuracies
    if round(sum(split_ratio_dict.values()), 15) != 1:
        raise AssertionError("Split ratios must sum up to 1.")


def check_split_ratio_keys(split_ratio_dict: Dict[Text, Any]):
    """
    Small helper to validate a split ratio dictionary by its keys.
    Allowed: Either train + eval, train + eval + test, or nosplit keys.
    """
    # Get fold names
    split_folds = list(split_ratio_dict.keys())
    num_folds = len(split_folds)

    required_folds = []

    if not split_folds:
        raise AssertionError("Error: The given split ratio "
                             "dictionary is empty.")

    # nosplit case
    if num_folds == 1:
        required_folds = [constants.NOSPLIT]

    elif num_folds == 2:
        required_folds = [constants.TRAIN, constants.EVAL]

    elif num_folds == 3:
        required_folds = [constants.TRAIN, constants.EVAL, constants.TEST]

    elif num_folds > 3:
        raise AssertionError(
            "Error: More than three fold keys are not supported at the "
            "moment.")

    if not required_folds:
        raise AssertionError(
            "Error: Something went wrong while validating the split ratio "
            "dict."
            "This should not happen. Contact a maiot GmbH engineer "
            "immediately!")

    if not all(str(fold) in required_folds for fold in split_folds):
        raise AssertionError(
            "Error while validating the given ratio dict. Only the following "
            "fold names are supported "
            "when specifying {0} folds: ".format(num_folds)
            + '[%s]' % ', '.join(required_folds))


def validate_split_ratio_dict(split_ratio_dict: Dict[Text, Any]):
    check_split_ratio_sum(split_ratio_dict)
    check_split_ratio_keys(split_ratio_dict)


def validate_split_config(split_config):
    """
    Helper to validate the supplied split config in terms of its entries.
    This is to prohibit some pathological cases (can be expanded).
    """
    # ratio dict checks for vertical and horizontal split,
    # top-level ratio checks happen below
    for key in [SplitKeys.CATEGORIZE_BY_, SplitKeys.INDEX_BY_]:
        if key in split_config:
            split = split_config[key]
            if constants.RATIO in split:
                ratio_dict = split[constants.RATIO]
                validate_split_ratio_dict(ratio_dict)

    # top-level ratio dict exists
    if SplitKeys.RATIO_ in split_config:

        # keys in the top-level ratio dict
        top_level_ratio_dict = split_config[SplitKeys.RATIO_]

        # split ratio dict checks (sum + key consistency)
        validate_split_ratio_dict(top_level_ratio_dict)
        top_level_folds = list(top_level_ratio_dict.keys())

        # disallow all three ratio dicts to be set simultaneously
        if SplitKeys.CATEGORIZE_BY_ in split_config:
            # get the config for horizontal split
            categorize_by_cfg = split_config[SplitKeys.CATEGORIZE_BY_]
            if constants.RATIO in categorize_by_cfg:
                category_ratio_dict = categorize_by_cfg[constants.RATIO]

                categorize_by_folds = list(
                    category_ratio_dict.keys())
                # set comprehension to validate ratio dicts
                if not set(categorize_by_folds) == set(top_level_folds):
                    # Print the keys creating the error for verbosity
                    # to help the user
                    set_diff = (set(categorize_by_folds) - set(
                        top_level_folds)) \
                               or (set(top_level_folds) - set(
                        categorize_by_folds))
                    raise AssertionError(
                        "Error: Ratio dict inconsistency detected. Please "
                        "check that you "
                        "supply the same keys for each split ratio entry in "
                        "the config. Keys that do not appear in both ratio"
                        "dicts: {}".format(set_diff))

            if constants.CATEGORIES in categorize_by_cfg:
                categories = categorize_by_cfg[constants.CATEGORIES]
                # disallow category specification and top-level split at the
                # same time
                if isinstance(categories, dict):
                    raise AssertionError(
                        "Error: Specifying a top-level split ratio and a "
                        "category dict at the same time is "
                        "disallowed.")

            if SplitKeys.INDEX_BY_ in split_config:
                # get the config for vertical split
                index_by_cfg = split_config[SplitKeys.INDEX_BY_]

                # disallow all ratio dicts to be set simultaneously
                if all(constants.RATIO in cfg for cfg in
                       [index_by_cfg, categorize_by_cfg]):
                    raise AssertionError(
                        "Error: Illegal ratio specification detected."
                        "Either drop the top-level \'ratio\' config key or "
                        "the lower-level index-by \'ratio\' key.")

        # disallow top-level ratio dict and index_by ratio dict to be set
        # simultaneously
        if SplitKeys.INDEX_BY_ in split_config:
            index_by_cfg = split_config[SplitKeys.INDEX_BY_]
            if constants.RATIO in index_by_cfg:
                raise AssertionError("Illegal ratio specification detected. "
                                     "Specifying a top-level split ratio "
                                     "and an index-by ratio at the "
                                     "same time is not supported.")

    else:  # no top-level ratio dict
        if SplitKeys.CATEGORIZE_BY_ in split_config:
            # get the config for horizontal split
            categorize_by_cfg = split_config[SplitKeys.CATEGORIZE_BY_]
            if constants.CATEGORIES in categorize_by_cfg:
                categories = categorize_by_cfg[constants.CATEGORIES]
                if isinstance(categories, dict):
                    if constants.RATIO in categorize_by_cfg:
                        # disallow category specification and category split at
                        # the same time
                        raise AssertionError(
                            "Error: Specifying a category split ratio and a "
                            "category dict "
                            "at the same time is disallowed.")

                    if constants.NOSPLIT in categories:
                        # handle the case where nosplit is specified along with
                        # other options as an error
                        if len(categories.keys()) > 1:
                            raise AssertionError(
                                "Error: When specifying \'nosplit\', passing "
                                "other fold keys is disallowed.")

                elif isinstance(categories, list):
                    if constants.RATIO not in categorize_by_cfg:
                        raise AssertionError(
                            "Error: When passing a list, the category split "
                            "ratio has to be specified,"
                            "either by a top-level or by a "
                            "category-level ratio dict.")

            else:
                # no top-level or category ratio keys specified
                if constants.RATIO not in categorize_by_cfg:
                    raise AssertionError(
                        "Error: When passing a list, the category split ratio "
                        "has to be specified,"
                        "either by a top-level or "
                        "by a category-level ratio dict.")

            if SplitKeys.INDEX_BY_ in split_config:
                # get the config for vertical split
                index_by_cfg = split_config[SplitKeys.INDEX_BY_]
                if all(constants.RATIO in cfg for cfg in
                       [index_by_cfg, categorize_by_cfg]):

                    category_ratio_dict = categorize_by_cfg[constants.RATIO]
                    idx_ratio_dict = index_by_cfg[constants.RATIO]

                    categorize_by_folds = list(
                        category_ratio_dict.keys())
                    index_by_folds = list(idx_ratio_dict.keys())
                    # set comprehension to validate ratio dicts
                    if not set(categorize_by_folds) == set(index_by_folds):
                        # Print the keys creating the error for verbosity
                        # to help the user
                        set_diff = (set(categorize_by_folds) - set(
                            index_by_folds)) or \
                                   (set(index_by_folds) - set(
                                       categorize_by_folds))
                        raise AssertionError(
                            "Error: Ratio dict inconsistency detected. Please "
                            "check that you supply the same keys for "
                            "each split ratio entry in the config. "
                            "Keys that do not appear in both ratio "
                            "dicts: {}".format(set_diff))

                if constants.RATIO in index_by_cfg:
                    idx_ratio_dict = index_by_cfg[constants.RATIO]

                    index_by_folds = list(idx_ratio_dict.keys())
                    if constants.CATEGORIES in categorize_by_cfg:
                        categories = categorize_by_cfg[constants.CATEGORIES]
                        if isinstance(categories, dict):
                            # set comprehension to validate category dict
                            # and index ratio dict
                            categorize_by_folds = list(categories.keys())
                            if not set(categorize_by_folds) == set(
                                    index_by_folds):
                                # Print the keys creating the error
                                # for verbosity to help the user
                                set_diff = (set(categorize_by_folds) - set(
                                    index_by_folds)) \
                                           or (set(index_by_folds) - set(
                                    categorize_by_folds))
                                raise AssertionError(
                                    "Error: Ratio dict inconsistency "
                                    "detected. Please check that you "
                                    "supply the same keys for each split"
                                    " ratio entry in the config. Keys that"
                                    " do not appear in both ratio "
                                    "dicts: {}".format(set_diff))
                        elif isinstance(categories, list):
                            if constants.RATIO not in categorize_by_cfg:
                                raise AssertionError(
                                    "Error: When passing a list, the category"
                                    " split ratio has to be specified,"
                                    "either by a top-level or by a "
                                    "category-level ratio dict.")


def get_cat_len_map(exec_properties):
    """
    Initial query to get count of data per category
    :return: dict of type { category: num_datapoints_in_category }
    """
    client = bigquery.Client()

    bq_args = extract_bq_args(exec_properties)
    cat_col = exec_properties[constants.CAT_COL]

    # TODO: [HIGH] Since the categories (eval and train) are hashed, we
    #  have to derive them from the config every time, remove this very
    #  ugly hack
    category_dict = infer_cats(bq_args=bq_args, split_config=None)

    # Dummy query to get the type information for each field.
    if cat_col:
        query = 'SELECT {cat_col}, COUNT({cat_col}) as count FROM ' \
                '`{project}.{dataset}.{table}` '.format(
            project=bq_args['project'],
            table=bq_args['table'],
            dataset=bq_args['dataset'],
            cat_col=cat_col)
        query = handle_where(query,
                             category_column=exec_properties[
                                 constants.CAT_COL],
                             category_dict=category_dict,
                             extras=exec_properties[constants.WHERE])
        query = query + ' GROUP BY {cat_col}'.format(cat_col=cat_col)
        query_job = client.query(query)
        return {row[cat_col]: row['count'] for row in query_job.result()}
    else:
        query = 'SELECT COUNT(*) as count FROM ' \
                '`{project}.{dataset}.{table}`'.format(
            project=bq_args['project'],
            dataset=bq_args['dataset'],
            table=bq_args['table'])
        query = handle_where(query,
                             category_column=exec_properties[
                                 constants.CAT_COL],
                             category_dict=category_dict,
                             extras=exec_properties[constants.WHERE])
        query_job = client.query(query)
        # Just need to loop for dtype consistency
        return {constants.DEFAULT_CATEGORY: row['count']
                for row in query_job.result()}


# TODO: This needs a complete rewrite, bisect does not do what it is
#  designed for in this setting
def get_limit_map(exec_properties):
    id_len_map = get_cat_len_map(exec_properties)

    # TODO: Hardcoded variables :(
    possible_idx_ratio_keys = [constants.I_RATIO_TRAIN,
                               constants.I_RATIO_EVAL,
                               constants.I_RATIO_TEST,
                               constants.I_RATIO_NOSPLIT]

    conversion_dict = {constants.I_RATIO_TRAIN: constants.TRAIN,
                       constants.I_RATIO_EVAL: constants.EVAL,
                       constants.I_RATIO_TEST: constants.TEST,
                       constants.I_RATIO_NOSPLIT: constants.NOSPLIT}

    limit_map = {}
    for k, v in id_len_map.items():
        ratio = 0
        limit_dict = {}
        for i_ratio_key in possible_idx_ratio_keys:
            i_ratio = exec_properties[i_ratio_key]
            if i_ratio is not None:
                ratio += i_ratio
                converted_key = conversion_dict[i_ratio_key]
                # this check is an artifact induced by the bisect.bisect
                # function in our custom Beam PartitionFn.
                # The right endpoint of the last fold (equal to the total
                # number of data points) in the limit dict
                # needs to be shifted by one so that bisect does not
                # create another split fold, which it would do for the
                # last row because the buckets are
                # half-open intervals B = [a,b).
                if isclose(ratio, 1.0):
                    limit_dict[converted_key] = v * ratio + 1
                else:
                    limit_dict[converted_key] = v * ratio

        limit_map[k] = limit_dict

    return limit_map


def extract_bq_args(exec_prop):
    return {'project': exec_prop[constants.BQ_PROJECT],
            'dataset': exec_prop[constants.BQ_DATASET],
            'table': exec_prop[constants.BQ_TABLE]}


def get_possible_categories(bq_args, cat_col):
    client = bigquery.Client()
    query_job = client.query(
        'SELECT DISTINCT ({cat_col}) as category '
        'FROM `{project}.{dataset}.{table}`'.format(
            project=bq_args['project'],
            table=bq_args['table'],
            dataset=bq_args['dataset'],
            cat_col=cat_col))
    return [row['category'] for row in query_job.result()]


def handle_features(features):
    if features is None:
        query_features = '*'
    elif isinstance(features, list):
        # In case we extend the standard for "defaults" reflect that here:
        query_features = features.copy()
        query_features = ",".join(list(set(query_features)))
    else:
        raise Exception(
            'You reached what I thought to be an unreachable state. '
            'I could give you advice what to do, but why would you trust me? '
            'Clearly I screwed this up - I am writing a message that should '
            'never appear, and yet it just did. '
            'I should stop coding and become a carpenter. Sorry!')
    return query_features


def handle_where(query,
                 category_column,
                 category_dict,
                 extras):
    where_clauses = []

    if extras is not None:
        harmful_sql = ['drop', 'update', 'truncate', 'commit', 'select',
                       'insert', 'create', 'alter']
        for clause in extras:
            if any(x in clause.lower().split() for x in harmful_sql):
                raise AssertionError('Dangerous SQL in WHERE '
                                     'clause: {}'.format(clause))
            where_clauses.append(clause)

    if any(len(cat_list) > 0 for cat_list in category_dict.values()):
        categories = []
        for cat_list in category_dict.values():
            categories = categories + cat_list  # add train, eval,
            # test category lists
        categories_str = [str(x) for x in categories]
        if type(categories[0]) is str:
            # if its string we wrap it around double quotes
            categories_joined = '"' + '","'.join(categories_str) + '"'
        else:
            # if numeric we dont wrap
            categories_joined = ','.join(categories_str)

        clause = '{column} in ({categories})'.format(
            column=category_column,
            categories=categories_joined)
        where_clauses.append(clause)

    if len(where_clauses):
        query += 'WHERE '
        query += " and ".join(where_clauses)

    return query


def parse_query(exec_properties, ce_config=None):
    bq_args = extract_bq_args(exec_properties)

    cat_col = exec_properties[constants.CAT_COL]
    idx_col = exec_properties[constants.IDX_COL]

    cols_to_select = [DATA_COL]

    cat_query = ''
    if cat_col:
        cols_to_select.append(cat_col)
        cat_query = 'PARTITION BY {}'.format(cat_col)

    idx_query = ''
    if idx_col:
        cols_to_select.append(idx_col)
        idx_query = 'ORDER BY {}'.format(idx_col)

    query = '''SELECT {features}, 
               ROW_NUMBER() OVER ({cat_query} {idx_query}) as {dfn}
               FROM `{project}.{dataset}.{table}`
               '''.format(
        features=','.join(list(set(cols_to_select))),
        project=bq_args['project'],
        dataset=bq_args['dataset'],
        table=bq_args['table'],
        cat_query=cat_query,
        idx_query=idx_query,
        dfn=constants.DEFAULT_ROW_NUMBER)

    category_dict = infer_cats(bq_args, ce_config)

    query = handle_where(query,
                         category_column=cat_col,
                         category_dict=category_dict,
                         extras=exec_properties[constants.WHERE])

    if exec_properties[constants.TEST_MODE]:
        query = query + ' LIMIT {}'.format(constants.LIMIT)

    absl.logging.warning(query)
    return query


def infer_cats(bq_args, split_config):
    if split_config is None:
        split_config = json.loads(os.getenv(ZENML_PIPELINE_CONFIG))[
            GlobalKeys.SPLIT]

    cat_dict = {}

    if SplitKeys.CATEGORIZE_BY_ in split_config:
        categorize_by_cfg = split_config[SplitKeys.CATEGORIZE_BY_]

        if constants.CATEGORIES in categorize_by_cfg:
            categories = categorize_by_cfg[constants.CATEGORIES]
            if isinstance(categories, dict):
                # sort the category lists and then that's it
                cat_dict = {k: sorted(l) for k, l in categories.items()}

            elif isinstance(categories, list):
                categories = sorted(categories)

                if SplitKeys.RATIO_ in split_config:
                    c_ratio = split_config[SplitKeys.RATIO_]
                else:
                    c_ratio = categorize_by_cfg[constants.RATIO]

                cat_dict = partition_cat_list(categories, c_ratio)

    # map fold keys to category dict keys
    cat_converter = {constants.TRAIN: constants.CAT_TRAIN,
                     constants.EVAL: constants.CAT_EVAL,
                     constants.TEST: constants.CAT_TEST,
                     constants.NOSPLIT: constants.CAT_NOSPLIT}

    mapped_dict = {cat_converter[k]: v for k, v in cat_dict.items()}

    return mapped_dict


def map_cat_to_fold(cat, cat_map) -> int:
    """
    Small helper to map folds to integers in the Partition Function.
    """
    folds = [constants.CAT_TRAIN, constants.CAT_EVAL, constants.CAT_TEST,
             constants.CAT_NOSPLIT]

    for i, fold in enumerate(folds):
        if fold in cat_map:
            fold_list = cat_map[fold]
            if not isinstance(fold_list, list):
                raise AssertionError("Error: Expected list but got element "
                                     "of type {}".format(type(fold_list)))
            if cat in fold_list:
                # this hack puts nosplit as fold zero, avoiding
                # problems with the Beam partition function
                # (in our workloads, nosplit does not appear together
                # with other folds, so this should be fine)
                return i % 3

    # case where the category is not in any fold
    return -1


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


def get_category_map(exec_properties):
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
        # extract BQ args and categorical column
        bq_args = extract_bq_args(exec_properties)

        cat_col = exec_properties[constants.CAT_COL]

        # infer categories by dummy BQ query
        categories = sorted(get_possible_categories(bq_args, cat_col))

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
        bq_args = extract_bq_args(exec_properties)

        cat_col = exec_properties[constants.CAT_COL]

        # Query to infer cat types
        categories = sorted(get_possible_categories(bq_args, cat_col))

        # TODO: Can it happen that multiple categories out of a BigQuery job
        #  have different dtypes? Then this is not good
        cat_type = type(categories[0])

        cat_dict = {key: exec_properties[key].split(",") for key in cat_keys
                    if exec_properties[key] is not None}

        for key, cat_list in cat_dict.items():
            cat_dict[key] = [cat_type(cat) for cat in cat_list]

        mapped_dict = cat_dict

    return mapped_dict
