from abc import abstractmethod
from typing import Any, Dict, List, Optional, Union

import numpy as np

Array_Like = Union[np.ndarray, List[Any], str, bytes, Dict[str, Any]]


class ZenMLCustomModel(object):
    """
    Model template. You can load your model parameters in __init__ from a location accessible at runtime
    """

    def __init__(self, model_uri: str) -> None:
        """
        Add any initialization parameters. These will be passed at runtime from the graph definition parameters defined in your seldondeployment kubernetes resource manifest.
        """
        print("Initializing")

        self.model_uri = model_uri
        self.model = None
        self.ready = False
        self.load()

    @abstractmethod
    def load(self) -> None:
        """
        Load model from file

        Parameters
        ----------
        model_path : str
        """
        raise NotImplementedError

    @abstractmethod
    def predict(
        self,
        X: Array_Like,
        features_names: Optional[List[str]],
    ) -> Array_Like:
        """
        Return a prediction.

        Parameters
        ----------
        X : array-like
        feature_names : array of feature names (optional)
        """
        raise NotImplementedError
