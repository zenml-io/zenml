from typing import Text, Dict

from playground.base_step import BaseStep


def lint_split_map(split_map: Dict[Text, float]):
    """Small utility to lint the split_map"""
    if len(split_map) <= 1:
        raise AssertionError(
            'Please specify more than 1 split name in the '
            'split_map!')

    if not all(isinstance(v, (int, float)) for v in split_map.values()):
        raise AssertionError("Only int or float values are allowed when "
                             "specifying a random split!")


class SplitStep(BaseStep):
    def __init__(self, split_map: Dict[Text, float]):
        lint_split_map(split_map)
        self.split_map = split_map

        super().__init__()

    def process(self,
                input_data,
                output_data, ):
        # read the data using the input artifact

        # split the data with custom logic and params
        self.split_map = 'some logics'

        # write the results using the output artifact
        pass

# class DistributedSplitStep(DistributedBaseStep):
#     """
#     Random split. Use this to randomly split data based on a cumulative
#     distribution function defined by a split_map dict.
#     """
#
#     def __init__(self,
#                  split_map: Dict[Text, float]):
#
#         lint_split_map(split_map)
#         self.split_map = split_map
#
#         super().__init__()
#
#     def __call__(self, *args, **kwargs):
#
#         # if SKIP in split_names:
#         #     sanitized_names = [name for name in split_names if name != SKIP]
#         #     examples_artifact.split_names = artifact_utils.encode_split_names(
#         #         sanitized_names)
#         # else:
#         #     examples_artifact.split_names = artifact_utils.encode_split_names(
#         #         split_names)
#         #
#         # split_uris = []
#         # for artifact in input_dict[constants.INPUT_EXAMPLES]:
#         #     for split in artifact_utils.decode_split_names(
#         #             artifact.split_names):
#         #         uri = os.path.join(artifact.uri, f'Split-{split}')
#         #         split_uris.append((split, uri))
#         #
#         pass
#
#     def partition_fn(self,
#                      element: Any,
#                      num_partitions: int) -> int:
#         """
#         Function for a random split of the data; to be used in a beam.Partition.
#         This function implements a simple random split algorithm by drawing
#         integers from a categorical distribution defined by the values in
#         split_map.
#
#         Args:
#             element: Data point, in format tf.train.Example.
#             num_partitions: Number of splits, unused here.
#
#         Returns:
#             An integer n, where 0 ≤ n ≤ num_partitions - 1.
#         """
#
#         # calculates probability mass of each split
#         probability_mass = np.cumsum(list(self.split_map.values()))
#         max_value = probability_mass[-1]
#
#         return bisect.bisect(probability_mass,
#                              np.random.uniform(0, max_value))
#
#     def get_split_names(self) -> List[Text]:
#         return list(self.split_map.keys())
#
#     def to_component(self,
#                      schema: SchemaArtifact,
#                      statistics: StatisticsArtifact,
#                      input_data: DataArtifact,
#                      output_data: DataArtifact,
#                      ):
#
#         # infer the names of the splits from the config
#         split_names = self.get_split_names()
#
#         # Get output split path
#         with self._make_beam_pipeline() as p:
#             # The outer loop will for now only run once
#             for split, uri in split_uris:
#                 input_uri = io_utils.all_files_pattern(uri)
#
#                 new_splits = (
#                         p
#                         | 'ReadData.' + split >> beam.io.ReadFromTFRecord(
#                     file_pattern=input_uri)
#                         | beam.Map(tf.train.Example.FromString)
#                         | 'Split' >> beam.Partition(split_step.partition_fn,
#                                                     split_step.get_num_splits()))
#
#                 for split_name, new_split in zip(split_names,
#                                                  list(new_splits)):
#                     if split_name != SKIP:
#                         # WriteSplit function writes to TFRecord again
#                         (new_split
#                          | 'Serialize.' + split_name >> beam.Map(
#                                     lambda x: x.SerializeToString())
#                          | 'WriteSplit_' + split_name >> WriteSplit(
#                                     get_split_uri(
#                                         output_dict[constants.OUTPUT_EXAMPLES],
#                                         split_name)))
