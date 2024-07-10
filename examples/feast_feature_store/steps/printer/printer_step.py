import pandas as pd

from zenml import step


@step
def feature_printer(
    historical_features: pd.DataFrame,
) -> pd.DataFrame:
    """Prints features imported from the offline / batch feature store."""
    return historical_features.head()
