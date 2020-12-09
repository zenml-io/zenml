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

from typing import Dict, Text, Any

from zenml.core.pipelines.config.standard_config import SplitKeys

TRAIN = 'train'
EVAL = 'eval'
TEST = 'test'
NOSPLIT = 'nosplit'
RATIO = 'ratio'
CATEGORIES = 'categories'
BY = 'by'


def check_split_ratio_sum(split_ratio_dict: Dict[Text, Any]):
    # using round because of float inaccuracies
    """
    Args:
        split_ratio_dict:
    """
    if round(sum(split_ratio_dict.values()), 15) != 1:
        raise AssertionError("Split ratios must sum up to 1.")


def check_split_ratio_keys(split_ratio_dict: Dict[Text, Any]):
    """Small helper to validate a split ratio dictionary by its keys. Allowed:
    Either train + eval, train + eval + test, or nosplit keys.

    Args:
        split_ratio_dict:
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
        required_folds = [NOSPLIT]

    elif num_folds == 2:
        required_folds = [TRAIN, EVAL]

    elif num_folds == 3:
        required_folds = [TRAIN, EVAL, TEST]

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
    """
    Args:
        split_ratio_dict:
    """
    check_split_ratio_sum(split_ratio_dict)
    check_split_ratio_keys(split_ratio_dict)


def validate_split_config(split_config):
    """Helper to validate the supplied split config in terms of its entries.
    This is to prohibit some pathological cases (can be expanded).

    Args:
        split_config:
    """
    # ratio dict checks for vertical and horizontal split,
    # top-level ratio checks happen below
    for key in [SplitKeys.CATEGORIZE_BY_, SplitKeys.INDEX_BY_]:
        if key in split_config:
            split = split_config[key]
            if RATIO in split:
                ratio_dict = split[RATIO]
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
            if RATIO in categorize_by_cfg:
                category_ratio_dict = categorize_by_cfg[RATIO]

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

            if CATEGORIES in categorize_by_cfg:
                categories = categorize_by_cfg[CATEGORIES]
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
                if all(RATIO in cfg for cfg in
                       [index_by_cfg, categorize_by_cfg]):
                    raise AssertionError(
                        "Error: Illegal ratio specification detected."
                        "Either drop the top-level \'ratio\' config key or "
                        "the lower-level index-by \'ratio\' key.")

        # disallow top-level ratio dict and index_by ratio dict to be set
        # simultaneously
        if SplitKeys.INDEX_BY_ in split_config:
            index_by_cfg = split_config[SplitKeys.INDEX_BY_]
            if RATIO in index_by_cfg:
                raise AssertionError("Illegal ratio specification detected. "
                                     "Specifying a top-level split ratio "
                                     "and an index-by ratio at the "
                                     "same time is not supported.")

    else:  # no top-level ratio dict
        if SplitKeys.CATEGORIZE_BY_ in split_config:
            # get the config for horizontal split
            categorize_by_cfg = split_config[SplitKeys.CATEGORIZE_BY_]
            if CATEGORIES in categorize_by_cfg:
                categories = categorize_by_cfg[CATEGORIES]
                if isinstance(categories, dict):
                    if RATIO in categorize_by_cfg:
                        # disallow category specification and category split at
                        # the same time
                        raise AssertionError(
                            "Error: Specifying a category split ratio and a "
                            "category dict "
                            "at the same time is disallowed.")

                    if NOSPLIT in categories:
                        # handle the case where nosplit is specified along with
                        # other options as an error
                        if len(categories.keys()) > 1:
                            raise AssertionError(
                                "Error: When specifying \'nosplit\', passing "
                                "other fold keys is disallowed.")

                elif isinstance(categories, list):
                    if RATIO not in categorize_by_cfg:
                        raise AssertionError(
                            "Error: When passing a list, the category split "
                            "ratio has to be specified,"
                            "either by a top-level or by a "
                            "category-level ratio dict.")

            else:
                # no top-level or category ratio keys specified
                if RATIO not in categorize_by_cfg:
                    raise AssertionError(
                        "Error: When passing a list, the category split ratio "
                        "has to be specified,"
                        "either by a top-level or "
                        "by a category-level ratio dict.")

            if SplitKeys.INDEX_BY_ in split_config:
                # get the config for vertical split
                index_by_cfg = split_config[SplitKeys.INDEX_BY_]
                if all(RATIO in cfg for cfg in
                       [index_by_cfg, categorize_by_cfg]):

                    category_ratio_dict = categorize_by_cfg[RATIO]
                    idx_ratio_dict = index_by_cfg[RATIO]

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

                if RATIO in index_by_cfg:
                    idx_ratio_dict = index_by_cfg[RATIO]

                    index_by_folds = list(idx_ratio_dict.keys())
                    if CATEGORIES in categorize_by_cfg:
                        categories = categorize_by_cfg[CATEGORIES]
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
                            if RATIO not in categorize_by_cfg:
                                raise AssertionError(
                                    "Error: When passing a list, the category"
                                    " split ratio has to be specified,"
                                    "either by a top-level or by a "
                                    "category-level ratio dict.")
