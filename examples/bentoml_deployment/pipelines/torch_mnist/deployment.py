import numpy as np
import bentoml
from bentoml.io import NumpyNdarray, Image
from PIL.Image import Image as PILImage

from zenml.integrations.bentoml import BentoMLIntegration
from zenml.integrations.bentoml.custom_deployer import ZenMLCustomModel

mnist_runner = bentoml.pytorch.get("demo_mnist:latest").to_runner()

svc = ZenMLCustomModel("pytorch_mnist", mnist_runner)

@svc.api(input=Image(), output=NumpyNdarray(dtype="int64"))
def predict(input_img: PILImage):
    img_arr = np.array(input_img)/255.0
    input_arr = np.expand_dims(img_arr, 0).astype("float32")
    output_tensor = mnist_runner.predict.run(input_arr)
    return output_tensor.numpy()
