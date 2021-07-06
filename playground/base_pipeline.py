import time
from abc import abstractmethod
from typing import Optional, Text, List

from playground.base_step import BaseStep
from zenml.backends.orchestrator import OrchestratorBaseBackend
from zenml.datasources import BaseDatasource

from zenml.metadata import ZenMLMetadataStore
from zenml.repo import Repository


class BasePipeline:
    def __init__(self,
                 name: Text = None,
                 backend: OrchestratorBaseBackend = None,
                 datasource: Optional[BaseDatasource] = None,
                 datasource_commit_id: Optional[Text] = None,
                 enable_cache: Optional[bool] = True):
        # Parameters
        self.enable_cache = enable_cache
        self.backend = backend

        if name is None:
            name = str(round(time.time() * 1000))
        self.name = name

        # Stores TODO: Change the extraction
        self.metadata_store: ZenMLMetadataStore = \
            Repository.get_instance().get_default_metadata_store()
        self.artifact_store = \
            Repository.get_instance().get_default_artifact_store()

        # Datasource
        if datasource:
            self.datasource = datasource
            self.datasource_commit_id = datasource.get_latest_commit()
        else:
            self.datasource = None
            self.datasource_commit_id = None

        if datasource_commit_id:
            self.datasource_commit_id = datasource_commit_id

    def run(self):
        pass

    @abstractmethod
    def connect(self):
        pass
