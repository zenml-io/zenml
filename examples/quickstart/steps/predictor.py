from typing import Annotated

from zenml import step
from zenml.services import BaseService


@step
def predictor(
    service: BaseService,
    data: pd.DataFrame,
) -> Annotated[list, "predictions"]:
    """Run a inference request against a prediction service."""
    service.start(timeout=10)  # should be a NOP if already started
    print(
        f"Running predictions on data (single individual): {data.to_numpy()[0]}"
    )
    prediction = service.predict(data.to_numpy())
    print(
        f"Prediction (for single example slice) is: {bool(prediction.tolist()[0])}"
    )
    return prediction.tolist()
