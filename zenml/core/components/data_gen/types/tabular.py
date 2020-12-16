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

from typing import Dict, Text, Any

import apache_beam as beam

from zenml.core.components.data_gen.constants import DestinationKeys
from zenml.core.components.data_gen.types.interface import TypeInterface
from zenml.core.components.data_gen.utils import DtypeInferrer
from zenml.core.components.data_gen.utils import append_tf_example
from zenml.core.components.data_gen.utils import init_bq_table


@beam.ptransform_fn
@beam.typehints.with_input_types(beam.typehints.Dict[Text, Any])
@beam.typehints.with_output_types(beam.pvalue.PDone)
def WriteToBQ(datapoints: Dict[Text, Any],
              schema: Dict[Text, Any],
              destination: Dict[Text, Any]) -> beam.pvalue.PDone:
    # Obtain the schema
    """
    Args:
        datapoints:
        schema:
        destination:
    """
    if schema:
        schema_dict = schema
        assert all(v in ['STRING', 'INTEGER', 'FLOAT', 'TIMESTAMP',
                         'BOOLEAN', 'BYTES']
                   for _, v in schema.items())
        init_bq_table(
            destination[DestinationKeys.PROJECT],
            destination[DestinationKeys.DATASET],
            destination[DestinationKeys.TABLE],
            schema)
    else:

        schema = (datapoints
                  | 'InferSchema' >> beam.CombineGlobally(
                    DtypeInferrer(),
                    project=destination[DestinationKeys.PROJECT],
                    dataset=destination[DestinationKeys.DATASET],
                    table=destination[DestinationKeys.TABLE]))
        schema_dict = beam.pvalue.AsSingleton(schema)

    return (datapoints
            | 'AddTFExample' >> beam.Map(append_tf_example, schema_dict)
            | 'WriteToBQ' >> beam.io.WriteToBigQuery(
                table=destination[DestinationKeys.TABLE],
                dataset=destination[DestinationKeys.DATASET],
                project=destination[DestinationKeys.PROJECT],
                write_disposition='WRITE_EMPTY')
            )


class TabularConverter(TypeInterface):
    def convert(self):
        return WriteToBQ
