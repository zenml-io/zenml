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
