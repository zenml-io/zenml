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

# Test limit
LIMIT = 1000

# Split names and types
TRAIN = 'train'
EVAL = 'eval'
TEST = 'test'  # new test split name
NOSPLIT = 'nosplit'  # nosplit

DEFAULT_ROW_NUMBER = 'default_row_number'
DEFAULT_CATEGORY = 'default_category'

# Namings for execution params
BQ_PROJECT = 'bq_project'
BQ_DATASET = 'bq_dataset'
BQ_TABLE = 'bq_table'
TEST_MODE = 'test_mode'
WHERE = 'where'
FEATURES = 'features'
CAT_COL = 'cat_col'
CAT_TRAIN = 'cat_train'
CAT_EVAL = 'cat_eval'
CAT_TEST = 'cat_test'  # new test category
CAT_NOSPLIT = 'cat_nosplit'
IDX_COL = 'idx_col'

# index ratio constants for categorical and index based
C_RATIO_TRAIN = 'c_ratio_train'
C_RATIO_EVAL = 'c_ratio_eval'
C_RATIO_TEST = 'c_ratio_test'
C_RATIO_NOSPLIT = 'c_ratio_nosplit'
I_RATIO_TRAIN = 'idx_ratio_train'
I_RATIO_EVAL = 'idx_ratio_eval'
I_RATIO_TEST = 'idx_ratio_test'
I_RATIO_NOSPLIT = 'idx_ratio_nosplit'

# Various CATEGORIZE_BY and INDEX_BY sub-keys
RATIO = "ratio"
CATEGORIES = "categories"
BY = "by"
