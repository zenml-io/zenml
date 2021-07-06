from abc import abstractmethod

from tfx.types import Artifact


class BaseArtifact(Artifact):
    @abstractmethod
    def read(self):
        pass

    @abstractmethod
    def write(self):
        pass
