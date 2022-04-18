from abc import abstractmethod


class ZenMLCustomModel(object):
    """
    Model template. You can load your model parameters in __init__ from a location accessible at runtime
    """

    def __init__(self, model_uri: str):
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
        print("Load called - will load from file")

    @abstractmethod
    def predict(self, X, features_names):
        """
        Return a prediction.

        Parameters
        ----------
        X : array-like
        feature_names : array of feature names (optional)
        """
        print("Predict called - will run identity function")
        return X
