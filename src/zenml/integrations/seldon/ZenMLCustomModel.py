import logging
from typing import Dict, List, Optional, Union, Iterable
import numpy as np


class ZenMLCustomModel(object):
    """
    Model template. You can load your model parameters in __init__ from a location accessible at runtime
    """

    def __init__(self, load_func: str, predict_func: str, model_uri: str = None):
        """
        Add any initialization parameters. These will be passed at runtime from the graph definition parameters defined in your seldondeployment kubernetes resource manifest.


        function_path: path to the python module that contains the predict function.
        E.g. if the function is `predict` and it's part of a user defined `pipeline.py` python module:
        """

        from zenml.utils.source_utils import load_source_path_class
        self.load_func = load_source_path_class(load_func)
        self.predict_func = load_source_path_class(predict_func)
        self.model = None
        self.ready = False
        self.model = self.load(model_uri)

    def load(self, model_uri: str):
        """
        Load the model from the given path.
        """
        try:
            self.model = self.load_func(model_uri)
            self.ready = True
        except Exception as ex:
            logging.exception("Exception during custom model loading")
        

    def predict(
        self,
        X: Union[np.ndarray, List, str, bytes, Dict],
        names: Optional[List[str]],
        meta: Optional[Dict] = None,
    ) -> Union[np.ndarray, List, str, bytes, Dict]:

        """
        Return a prediction.

        Parameters
        ----------
        X : array-like
        feature_names : array of feature names (optional)
        """
         
        return self.predict_func(X, names, meta)