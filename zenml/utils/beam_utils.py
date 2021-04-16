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

from typing import Text, Dict, Any

import apache_beam as beam
from tfx.components.example_gen.base_example_gen_executor import _WriteSplit

from zenml.components.data_gen import utils


@beam.ptransform_fn
@beam.typehints.with_input_types(beam.typehints.Dict[Text, Any])
@beam.typehints.with_output_types(beam.pvalue.PDone)
def WriteToTFRecord(datapoints: Dict[Text, Any],
                    schema: Dict[Text, Any],
                    output_split_path: Text) -> beam.pvalue.PDone:
    """Infers schema and writes to TFRecord"""
    # Obtain the schema
    if schema:
        schema_dict = {k: utils.SCHEMA_MAPPING[v] for k, v in schema.items()}
    else:
        schema = (datapoints
                  | 'Schema' >> beam.CombineGlobally(utils.DtypeInferrer()))
        schema_dict = beam.pvalue.AsSingleton(schema)

    return (datapoints
            | 'ToTFExample' >> beam.Map(utils.append_tf_example, schema_dict)
            | 'WriteToTFRecord' >> _WriteSplit(
                output_split_path=output_split_path
            ))
