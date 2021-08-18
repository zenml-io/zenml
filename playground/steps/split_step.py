# import os
# import types
# from abc import abstractmethod
# from typing import Type
#
# from playground.artifacts.data_artifacts import BaseDataArtifact
# from playground.steps.base_step import BaseStep
# from playground.steps.base_step import Input, Output, Param
#
#
# class BaseSplitStep(BaseStep):
#     @abstractmethod
#     def split_fn(self, *args, **kwargs):
#         pass
#
#     def process(self,
#                 input_data: Input[BaseDataArtifact],
#                 output_data: Output[BaseDataArtifact],
#                 split_map: Param[dict]):
#
#         # infer the names of the splits from the config
#         split_names = split_step.get_split_names()
#
#         # Get output split path
#         examples_artifact = artifact_utils.get_single_instance(
#             output_dict[constants.OUTPUT_EXAMPLES])
#         if SKIP in split_names:
#             sanitized_names = [name for name in split_names if name != SKIP]
#             examples_artifact.split_names = artifact_utils.encode_split_names(
#                 sanitized_names)
#         else:
#             examples_artifact.split_names = artifact_utils.encode_split_names(
#                 split_names)
#
#         split_uris = []
#         for artifact in input_dict[constants.INPUT_EXAMPLES]:
#             for split in artifact_utils.decode_split_names(
#                     artifact.split_names):
#                 uri = os.path.join(artifact.uri, f'Split-{split}')
#                 split_uris.append((split, uri))
#
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
#
#
# def SplitStep(func: types.FunctionType) -> Type:
#     step_class = type(func.__name__,
#                       (BaseSplitStep,),
#                       {"partition": staticmethod(func)})
#
#     return step_class
