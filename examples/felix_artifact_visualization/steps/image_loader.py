from PIL import Image

from zenml.steps import step

IMG_PATH = "docs/mkdocs/_assets/favicon.png"


@step
def image_loader() -> Image.Image:
    """Loads an image from a URL and returns it as a PIL Image."""
    img = Image.open(IMG_PATH)
    return img
