import os
from typing import Text, Dict, Any

import apache_beam as beam
import tensorflow as tf
from tfx.utils import io_utils
from tfx_bsl.coders import csv_decoder


@beam.ptransform_fn
@beam.typehints.with_input_types(beam.Pipeline)
@beam.typehints.with_output_types(beam.typehints.Dict[Text, Any])
def ReadFilesFromDisk(pipeline: beam.Pipeline,
                      source_args: Dict[Text, Any]) -> beam.pvalue.PCollection:
    base_path = source_args['base_path']

    wildcard_qualifier = "*"

    # we are ingesting all the files from the base path by
    # supplying the wildcard (hopefully?)
    file_pattern = os.path.join(base_path, wildcard_qualifier)

    csv_files = tf.io.gfile.glob(file_pattern)
    if not csv_files:
        raise RuntimeError(
            'Split pattern {} does not match any files.'.format(file_pattern))

    column_names = io_utils.load_csv_column_names(csv_files[0])

    parsed_csv_lines = (
            pipeline
            | 'ReadFromText' >> beam.io.ReadFromText(file_pattern=file_pattern,
                                                     skip_header_lines=1)
            | 'ParseCSVLine' >> beam.ParDo(csv_decoder.ParseCSVLine(
        delimiter=','))
            | 'ExtractParsedCSVLines' >> beam.Map(lambda x:
                                                  dict(zip(column_names, x))))

    return parsed_csv_lines


class LocalCSVSource(SourceInterface):
    ARG_KEYS = LocalCSVArgs

    def beam_transform(self):
        return ReadFilesFromDisk
