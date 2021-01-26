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

import re
from typing import Text


def to_dns1123(name: Text, length=253):
    if len(name) > length:
        name = name[:length]
    name = re.sub(r'[^a-z0-9-\.]([^a-z0-9]{0,61}[^a-z0-9])?', r'-', name)
    return name.lower()

def get_id(text: Text):
    id_pattern = r'[a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12}'
    matches = re.findall(id_pattern, text)
    if not matches:
        match = None
    else:  # limit to the first result to prevent weirdness
        match = matches[0]
    return match

