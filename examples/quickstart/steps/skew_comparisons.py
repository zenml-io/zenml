import numpy as np
import pandas as pd

from zenml.integrations.evidently.steps import (
    EvidentlyProfileConfig,
    EvidentlyProfileStep,
)
from zenml.steps import Output, step


@step
def skew_comparison(
    reference_input: np.ndarray,
    comparison_input: np.ndarray,
) -> Output(reference=pd.DataFrame, comparison=pd.DataFrame):
    """Convert data from numpy to pandas for skew comparison."""
    columns = [str(x) for x in list(range(reference_input.shape[1]))]
    return pd.DataFrame(reference_input, columns=columns), pd.DataFrame(
        comparison_input, columns=columns
    )


evidently_profile_config = EvidentlyProfileConfig(
    column_mapping=None, profile_sections=["datadrift"]
)
drift_detector = EvidentlyProfileStep(config=evidently_profile_config)
