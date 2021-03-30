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

from zenml.standards.standard_keys import StepKeys
from zenml.utils.source_utils import load_source_path_class


def run_fn(fn_args):
    fn_args_dict = fn_args.__dict__
    custom_config = fn_args_dict.pop('custom_config')

    # Get the user defined args
    args = custom_config.pop(StepKeys.ARGS)

    # We update users args first, because fn_args might have overlaps
    args.update(fn_args_dict)

    # Load the step, parameterize it and run it
    c = load_source_path_class(custom_config.pop(StepKeys.SOURCE))
    return c(**args).run_fn()
