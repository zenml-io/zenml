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
#
# # pylint disable=protected-access
#
# import os
# import shutil
# from pathlib import Path
#
# import pytest
#
# import zenml
#
# # from zenml.backends import BaseBackend
# # from zenml.datasources import BaseDatasource
# from zenml.logger import get_logger
#
# # from zenml.metadata import BaseMetadataStore
# # from zenml.pipelines import BasePipeline
# # from zenml.repo import Repository, ZenMLConfig
# # from zenml.steps import BaseStep
# # from zenml.utils import path_utils
#
# logger = get_logger(__name__)
#
# # Nicholas a way to get to the root
# ZENML_ROOT = str(Path(zenml.__path__[0]).parent)
# TEST_ROOT = os.path.join(ZENML_ROOT, "tests")
#
# pipeline_root = os.path.join(TEST_ROOT, "pipelines")
#
#
# @pytest.fixture
# def cleanup_metadata_store():
#     """Clean up metadata store."""
#
#     def wrapper():
#         """ """
#         # Remove metadata db after a test to avoid test failures by duplicated
#         # data sources
#         metadata_db_location = os.path.join(
#             ".zenml", "local_store", "metadata.db"
#         )
#         try:
#             os.remove(os.path.join(ZENML_ROOT, metadata_db_location))
#         except Exception as e:
#             logger.error(e)
#
#     return wrapper
#
#
# @pytest.fixture
# def cleanup_pipelines_dir():
#     """Clean up pipeline dir."""
#
#     def wrapper():
#         """ """
#         pipelines_dir = repo.zenml_config.get_pipelines_dir()
#         for p_config in fileio.list_dir(pipelines_dir):
#             try:
#                 os.remove(p_config)
#             except Exception as e:
#                 logger.error(e)
#
#     return wrapper
#
#
# @pytest.fixture
# def cleanup_artifacts():
#     """Cleanup artifacts."""
#
#     def wrapper():
#         """ """
#         local_store_path = os.path.join(".zenml", "local_store")
#         try:
#             local_store = os.path.join(ZENML_ROOT, local_store_path)
#             shutil.rmtree(local_store, ignore_errors=False)
#         except Exception as e:
#             logger.error(e)
#
#     return wrapper
#
#
# @pytest.fixture
# def cleanup(cleanup_metadata_store, cleanup_artifacts):
#     """Cleanup.
#
#     Args:
#       cleanup_metadata_store:
#       cleanup_artifacts:
#
#     Returns:
#
#     """
#     cleanup_metadata_store()
#     cleanup_artifacts()
#
#
# @pytest.fixture
# def delete_config():
#     """Delete the config."""
#
#     def wrapper(filename):
#         """
#
#         Args:
#           filename:
#
#         Returns:
#
#         """
#         cfg = os.path.join(pipeline_root, filename)
#         path_utils.rm_file(cfg)
#
#     return wrapper
#
#
# @pytest.fixture
# def equal_backends():
#     """Checks whether two backends are equal."""
#
#     def wrapper(bck1: BaseBackend, bck2: BaseBackend, loaded=True):
#         """
#
#         Args:
#           bck1: BaseBackend:
#           bck2: BaseBackend:
#           loaded:  (Default value = True)
#
#         Returns:
#
#         """
#         # There can be a "None" backend in a pipeline
#         if bck1 is None and bck2 is None:
#             return True
#         if sum(b is None for b in [bck1, bck2]) == 1:
#             return False
#
#         equal = False
#         equal |= bck1._kwargs == bck2._kwargs
#         equal |= bck1._source == bck2._source
#         if loaded:
#             equal |= bck1._immutable != bck2._immutable
#         else:
#             equal |= bck1._immutable == bck2._immutable
#
#         return equal
#
#     return wrapper
#
#
# @pytest.fixture
# def equal_steps(equal_backends):
#     """Check whether two steps are equal.
#
#     Args:
#       equal_backends:
#
#     Returns:
#
#     """
#
#     def wrapper(step1: BaseStep, step2: BaseStep, loaded=True):
#         """
#
#         Args:
#           step1: BaseStep:
#           step2: BaseStep:
#           loaded:  (Default value = True)
#
#         Returns:
#
#         """
#         # There can be a "None" step e.g. in get_data_step()
#         # in a BaseDatasource
#         if step1 is None and step2 is None:
#             return True
#         if sum(s is None for s in [step1, step2]) == 1:
#             return False
#
#         equal = False
#         equal |= step1._kwargs == step2._kwargs
#         equal |= equal_backends(step1.backend, step2.backend, loaded=loaded)
#         equal |= step1._source == step2._source
#         if loaded:
#             equal |= step1._immutable != step2._immutable
#         else:
#             equal |= step1._immutable == step2._immutable
#
#         return equal
#
#     return wrapper
#
#
# @pytest.fixture
# def equal_datasources(equal_steps):
#     """Check whether two datasources are equal.
#
#     Args:
#       equal_steps:
#
#     Returns:
#
#     """
#
#     def wrapper(ds1: BaseDatasource, ds2: BaseDatasource, loaded=True):
#         """
#
#         Args:
#           ds1: BaseDatasource:
#           ds2: BaseDatasource:
#           loaded:  (Default value = True)
#
#         Returns:
#
#         """
#         # There can be a "None" datasource in a pipeline
#         if ds1 is None and ds2 is None:
#             return True
#         if sum(d is None for d in [ds1, ds2]) == 1:
#             return False
#
#         equal = False
#         equal |= ds1.name == ds2.name
#         equal |= ds1._id == ds2._id
#         equal |= ds1._source == ds2._source
#         equal |= ds1._source_args == ds2._source_args
#
#         # TODO[LOW]: Add more checks for constructor kwargs, __dict__ etc.
#         if loaded:
#             equal |= ds1._immutable != ds2._immutable
#         else:
#             equal |= ds1._immutable == ds2._immutable
#
#         return equal
#
#     return wrapper
#
#
# @pytest.fixture
# def equal_pipelines(equal_backends, equal_steps, equal_datasources):
#     """Checks whether two pipelines are equal.
#
#     Args:
#       equal_backends:
#       equal_steps:
#       equal_datasources:
#
#     Returns:
#
#     """
#
#     def wrapper(p1: BasePipeline, p2: BasePipeline, loaded=True):
#         """Wrapper.
#
#         Args:
#           p1: BasePipeline:
#           p2: BasePipeline:
#           loaded:  (Default value = True)
#
#         Returns:
#
#         """
#         # There can be a "None" datasource in a pipeline
#         if p1 is None and p2 is None:
#             return True
#         if sum(p is None for p in [p1, p2]) == 1:
#             return False
#
#         equal = False
#         equal |= p1.name == p2.name
#         equal |= p1.PIPELINE_TYPE == p2.PIPELINE_TYPE
#         equal |= p1.pipeline_name == p2.pipeline_name
#         equal |= p1.enable_cache == p2.enable_cache
#         equal |= p1._source == p2._source
#         equal |= equal_backends(p1.backend, p2.backend, loaded=loaded)
#         equal |= equal_datasources(p1.datasource, p2.datasource, loaded=loaded)
#         if loaded:
#             equal |= p1._immutable != p2._immutable
#         else:
#             equal |= p1._immutable == p2._immutable
#         try:
#             for name, step in p1.steps_dict.items():
#                 p2_step = p2.steps_dict[name]
#                 equal |= equal_steps(step, p2_step, loaded=loaded)
#         except KeyError:
#             return False
#
#         return equal
#
#     return wrapper
#
#
# @pytest.fixture
# def equal_md_stores():
#     """Define equal md stores."""
#
#     def wrapper(md1: BaseMetadataStore, md2: BaseMetadataStore):
#         """
#
#         Args:
#           md1: BaseMetadataStore:
#           md2: BaseMetadataStore:
#
#         Returns:
#
#         """
#         # There can be a "None" datasource in a pipeline
#         if md1 is None and md2 is None:
#             return True
#         if sum(d is None for d in [md1, md2]) == 1:
#             return False
#         equal = False
#         equal |= md1.__dict__ == md2.__dict__
#         equal |= md1.metadata_store_type == md2.metadata_store_type
#
#         return equal
#
#     return wrapper
#
#
# @pytest.fixture
# def equal_zenml_configs(equal_md_stores):
#     """Check whether two zenml configs are equal.
#
#     Args:
#       equal_md_stores:
#
#     Returns:
#
#     """
#
#     def wrapper(cfg1: ZenMLConfig, cfg2: ZenMLConfig, loaded=True):
#         """
#
#         Args:
#           cfg1: ZenMLConfig:
#           cfg2: ZenMLConfig:
#           loaded:  (Default value = True)
#
#         Returns:
#
#         """
#         # There can be a "None" datasource in a pipeline
#         if cfg1 is None and cfg2 is None:
#             return True
#         if sum(d is None for d in [cfg1, cfg2]) == 1:
#             return False
#
#         # TODO[LOW]: Expand logic
#         equal = False
#         equal |= equal_md_stores(cfg1.metadata_store, cfg2.metadata_store)
#         equal |= cfg1.pipelines_dir == cfg2.pipelines_dir
#         equal |= cfg1.artifact_store.path == cfg2.artifact_store.path
#
#         return equal
#
#     return wrapper


import logging
import os

from zenml.constants import ENV_ZENML_DEBUG
from zenml.core.repo import Repository


def pytest_sessionstart(session):
    """Called after the Session object has been created and
    before performing collection and entering the run test loop.
    """
    os.environ[ENV_ZENML_DEBUG] = "true"
    try:
        Repository.init_repo()
    except AssertionError:
        # already initialized
        logging.info("Repo already initialized for testing.")


def pytest_sessionfinish(session, exitstatus):
    """Called after whole test run finished, right before
    returning the exit status to the system.
    """
