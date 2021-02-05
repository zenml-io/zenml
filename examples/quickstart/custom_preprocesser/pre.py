from typing import Dict

from zenml.core.steps.preprocesser.base_preprocesser import BasePreprocesserStep


class PreprocesserStep(BasePreprocesserStep):
    """
    Base class for all preprocessing steps. These steps are used to
    specify transformation and filling operations on data that occur before
    the machine learning model is trained.
    """


    def preprocessing_fn(self, inputs: Dict):
        """
        Function used in the Transform component. Override this to do custom
        preprocessing logic.

        Args:
            inputs (dict): Inputs where keys are feature names and values are
            tensors which represent the values of the features.

        Returns:
            outputs (dict): Inputs where keys are transformed feature names
             and values are tensors with the transformed values of the
             features.
        """
        return inputs
