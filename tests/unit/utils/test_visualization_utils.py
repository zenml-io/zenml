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

from bs4 import BeautifulSoup
from hypothesis import given
from hypothesis_csv.strategies import csv

from zenml.utils.visualization_utils import format_csv_visualization_as_html


@given(csv=csv())
def test_format_csv_visualization_as_html(csv):
    html = format_csv_visualization_as_html(csv)
    BeautifulSoup(html, "html.parser")  # will fail if not valid html
