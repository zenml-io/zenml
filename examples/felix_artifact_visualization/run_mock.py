from PIL import Image

from zenml.pipelines import pipeline
from zenml.steps import Output, step


@pipeline
def three_step_pipeline(get_image, get_markdown, get_html):
    get_image()
    get_markdown()
    get_html()


@step
def get_image() -> Output(image=Image.Image):
    return Image.open("docs/mkdocs/_assets/favicon.png")


@step
def get_markdown() -> Output(markdown=str):
    return "# Hello I am markdown\n\n## I am a header\n\nI am a paragraph"


@step
def get_html() -> Output(html=str):
    return "<html><body><h1>Hello I am HTML</h1></body></html>"


def main():
    pip = three_step_pipeline(
        get_image=get_image(),
        get_markdown=get_markdown(),
        get_html=get_html(),
    )
    pip.configure(enable_cache=False)
    pip.run()


if __name__ == "__main__":
    main()
