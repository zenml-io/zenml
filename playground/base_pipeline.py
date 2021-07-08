import time
from abc import abstractmethod
from typing import Optional, Text

from zenml.backends.orchestrator import OrchestratorBaseBackend
from zenml.datasources import BaseDatasource


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

        # Stores TODO: Shift the extraction to the client perhaps?
        self.metadata_store = None
        self.artifact_store = None

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
        step_list = self.connect(self.datasource)
        component_list = []
        for step in step_list:
            component_list.append(step.to_component())

    @abstractmethod
    def connect(self, *args, **kwargs):
        pass
