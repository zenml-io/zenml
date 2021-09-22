from abc import abstractmethod
from typing import Optional

from pydantic import BaseModel

from zenml.enums import OrchestratorTypes


class BaseOrchestrator(BaseModel):
    orchestrator_type: Optional[OrchestratorTypes] = OrchestratorTypes.base

    @abstractmethod
    def run(self, zenml_pipeline, **kwargs):
        pass
