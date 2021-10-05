#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
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

import os

from zenml.logger import init_logging

init_logging()
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

from .base import *  # noqa
from .config import *  # noqa

# from .example import *  # noqa
from .stack import *  # noqa
from .version import *  # noqa
