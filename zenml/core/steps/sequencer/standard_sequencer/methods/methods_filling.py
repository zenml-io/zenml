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

def forward_f():
    def apply(x):
        x = x.ffill()
        x = x.bfill()
        return x.fillna(infer_default_value(x))

    return apply


def backwards_f():
    def apply(x):
        x = x.bfill()
        x = x.ffill()
        return x.fillna(infer_default_value(x))

    return apply


def custom_f(custom_value):
    def apply(x):
        x = x.fillna(custom_value)
        return x

    return apply


def min_f():
    def apply(x):
        x = x.fillna(x.min())
        return x.fillna(infer_default_value(x))

    return apply


def max_f():
    def apply(x):
        x = x.fillna(x.max())
        return x.fillna(infer_default_value(x))

    return apply


def mean_f():
    def apply(x):
        x = x.fillna(x.mean())
        return x.fillna(infer_default_value(x))

    return apply


def infer_default_value(x):
    if x.dtype == float:
        return 0.0
    else:
        return 'None'
