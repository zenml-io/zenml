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

from zenml.utils.source_utils import load_source_path_class
from zenml.core.standards.standard_keys import StepKeys

def run_fn(fn_args):
    c = load_source_path_class(fn_args.pop(StepKeys.SOURCE))

    # Pop unnecessary args
    args = fn_args.pop(StepKeys.ARGS)

    # TODO: [LOW] Hard-coded
    fn_args.pop('data_accessor')

    # We update users args first, because fn_args might have overlaps
    args.update(fn_args)

    return c(**args).get_run_fn()()
