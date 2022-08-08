#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
from torchvision import transforms
from ts.torch_handler.image_classifier import ImageClassifier


class MNISTDigitClassifier(ImageClassifier):
    """
    MNISTDigitClassifier handler class. This handler extends class ImageClassifier from image_classifier.py, a
    default handler. This handler takes an image and returns the number in that image.
    Here the post-processing method has been overridden while others are reused from parent class.
    """

    image_processing = transforms.Compose(
        [transforms.ToTensor(), transforms.Normalize((0.1307,), (0.3081,))]
    )

    def __init__(self):
        super(MNISTDigitClassifier, self).__init__()

    def postprocess(self, data):
        """The post-processing of MNIST converts the predicted output response to a label.
        Args:
            data (list): The predicted output from the inference with probabilities is passed
            to the post-process function

        Returns:
            list: A list of dictionaries with predictions and explanations is returned
        """
        return data.argmax(1).tolist()
