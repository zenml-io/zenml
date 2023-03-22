import numpy as np
import pandas as pd
from PIL import Image

from zenml.steps import step


@step
def image_to_df(image: Image.Image) -> pd.DataFrame:
    colourPixels = image.convert("RGB")
    colourArray = np.array(colourPixels.getdata()).reshape(image.size + (3,))
    indicesArray = np.moveaxis(np.indices(image.size), 0, 2)
    allArray = np.dstack((indicesArray, colourArray)).reshape((-1, 5))
    df = pd.DataFrame(allArray, columns=["x", "y", "red", "green", "blue"])
    return df
