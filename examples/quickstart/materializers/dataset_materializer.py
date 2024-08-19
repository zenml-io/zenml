# # Apache Software License 2.0
# #
# # Copyright (c) ZenML GmbH 2024. All rights reserved.
# #
# # Licensed under the Apache License, Version 2.0 (the "License");
# # you may not use this file except in compliance with the License.
# # You may obtain a copy of the License at
# #
# # http://www.apache.org/licenses/LICENSE-2.0
# #
# # Unless required by applicable law or agreed to in writing, software
# # distributed under the License is distributed on an "AS IS" BASIS,
# # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# # See the License for the specific language governing permissions and
# # limitations under the License.
# #
# import os
# import tempfile
#
# from typing import Any, ClassVar, Type
# from datasets import Dataset, load_from_disk, load_dataset
#
# from zenml.io import fileio
# from zenml.materializers.base_materializer import BaseMaterializer
#
#
# class DatasetMaterializer(BaseMaterializer):
#     """Base class for ultralytics YOLO models."""
#
#     SKIP_REGISTRATION: ClassVar[bool] = True
#     ASSOCIATED_TYPES = (
#         Dataset,
#     )
#
#     def load(self, data_type: Type[Any]) -> Dataset:
#         """Reads a Dataset from a file in the artifact store.
#
#         Args:
#             data_type: A Dataset type.
#
#         Returns:
#             A Dataset object.
#         """
#         filepath = self.uri
#         if fileio.exists(os.path.join(filepath, 'dataset_info.json')):
#             # Load from disk if it's a saved Hugging Face dataset
#             return load_from_disk(filepath)
#         else:
#             # Assume it's a regular file (e.g., CSV) and load it
#             file_extension = os.path.splitext(filepath)[1].lower()
#             if file_extension == '.csv':
#                 return load_dataset('csv', data_files=filepath)
#             elif file_extension in ['.json', '.jsonl']:
#                 return load_dataset('json', data_files=filepath)
#             else:
#                 raise ValueError(f"Unsupported file format: {file_extension}")
#
#     def save(self, obj: Dataset) -> None:
#         """Creates a serialization for a Dataset object.
#
#         Args:
#             obj: A Dataset object
#         """
#         if not isinstance(obj, Dataset):
#             raise TypeError(f"Expected Dataset object, got {type(obj)}")
#
#         filepath = self.uri
#         with tempfile.TemporaryDirectory(prefix="zenml-temp-") as temp_dir:
#             tmp_path = os.path.join(temp_dir, "model.txt")
#
#             obj.save_to_disk(tmp_path)
#
#             fileio.copy(tmp_path, filepath)
