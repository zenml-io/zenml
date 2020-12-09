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

def create_new_cell(contents):
    """

    Args:
        contents:

    Returns:

    """
    import sys
    from IPython.core.getipython import get_ipython

    if 'ipykernel' not in sys.modules:
        raise EnvironmentError('The magic functions are only usable in a '
                               'Jupyter notebook.')

    shell = get_ipython()

    payload = dict(
        source='set_next_input',
        text=contents,
        replace=False,
    )
    shell.payload_manager.write_payload(payload, single=False)
