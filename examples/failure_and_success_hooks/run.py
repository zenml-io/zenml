#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

from pipelines import hook_pipeline
from steps import HookParams, get_first_num, get_random_int, subtract_numbers

if __name__ == "__main__":
    # Initialize a new pipeline run

    p1 = hook_pipeline(
        get_first_num=get_first_num(params=HookParams(fail=False)),
        get_random_int=get_random_int(),
        subtract_numbers=subtract_numbers(),
    )
    p1.run()

    p2 = hook_pipeline(
        get_first_num=get_first_num(params=HookParams(fail=True)),
        get_random_int=get_random_int(),
        subtract_numbers=subtract_numbers(),
    )
    p2.run()
