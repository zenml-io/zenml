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

import pandas as pd


def resample_mode():
    def apply(data):
        if isinstance(data, pd.Series) and not data.dropna().empty:
            value = data.value_counts().idxmax()
            if type(value) == bytes:
                return value.decode('utf-8')
            return float(value)
        return None

    return apply


def resample_mean():
    def apply(data):
        if isinstance(data, pd.Series) and not data.dropna().empty:
            return float(data.mean())
        return None

    return apply


def resample_median():
    def apply(data):
        if isinstance(data, pd.Series) and not data.dropna().empty:
            return float(data.median())
        return None

    return apply


def resample_thresholding(cond, c_value, threshold, set_value):
    def apply(data):
        if isinstance(data, pd.Series) and not data.dropna().empty:

            assert cond in ['greater', 'greater_or_equal', 'equal',
                            'less_or_equal', 'less', 'includes']

            if cond == 'greater':
                check = pd.Series(data > c_value).value_counts(normalize=True)
            elif cond == 'greater_or_equal':
                check = pd.Series(data >= c_value).value_counts(normalize=True)
            elif cond == 'equal':
                check = pd.Series(data == c_value).value_counts(normalize=True)
            elif cond == 'less_or_equal':
                check = pd.Series(data <= c_value).value_counts(normalize=True)
            elif cond == 'less':
                check = pd.Series(data < c_value).value_counts(normalize=True)
            elif cond == 'includes':
                check = pd.Series(c_value in data).value_counts(normalize=True)
            else:
                raise Exception('invalid condition {}'.format(cond))

            if True in check.index:
                if check[True] > threshold:
                    if type(set_value) is str:
                        return set_value
                    else:
                        return float(set_value)
            return None

    return apply


def get_output_dtype(input_dtype, method, params):
    if method == resample_thresholding:
        if type(params['set_value']) is str:
            return str
        else:
            return float
    if input_dtype == 'string':
        if method == resample_mode:
            return str
    return float
