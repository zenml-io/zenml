#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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

import base64
import sys
import tempfile
import webbrowser
from abc import abstractmethod

import pandas as pd
from facets_overview.generic_feature_statistics_generator import (
    GenericFeatureStatisticsGenerator,
)

from zenml.logger import get_logger
from zenml.utils import path_utils

logger = get_logger(__name__)


HTML_TEMPLATE = """
<iframe id='facets-iframe' width="100%" height="500px"></iframe>
<script>
  facets_iframe = document.getElementById('facets-iframe');
  facets_html = '<script src="https://cdnjs.cloudflare.com/ajax/libs/webcomponentsjs/1.3.3/webcomponents-lite.js"><\/script><link rel="import" href="https://raw.githubusercontent.com/PAIR-code/facets/master/facets-dist/facets-jupyter.html"><facets-overview proto-input="protostr"></facets-overview>';  # noqa
  facets_iframe.srcdoc = facets_html;
  facets_iframe.id = "";
  setTimeout(() => {
    facets_iframe.setAttribute('height', facets_iframe.contentWindow.document.body.offsetHeight + 'px')
  }, 1500)
</script>
"""


class FacetStatisticsVisualizer:
    """The base implementation of a ZenML Visualizer."""

    @abstractmethod
    def visualize(self, df: pd.DataFrame, magic: bool = False) -> None:
        """Method to visualize components"""
        proto = GenericFeatureStatisticsGenerator().ProtoFromDataFrames(
            [{"name": "Facet Overview", "table": df}]
        )
        protostr = base64.b64encode(proto.SerializeToString()).decode("utf-8")
        h = HTML_TEMPLATE.replace("protostr", protostr)

        if magic:

            if "ipykernel" not in sys.modules:
                raise EnvironmentError(
                    "The magic functions are only usable "
                    "in a Jupyter notebook."
                )
            from IPython.core.display import HTML, display

            display(HTML(h))
        else:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as f:
                path_utils.write_file_contents_as_string(f.name, h)
                url = f"file:///{f.name}"
                webbrowser.open(url, new=2)
