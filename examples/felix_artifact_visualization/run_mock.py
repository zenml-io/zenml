from PIL import Image

from zenml.pipelines import pipeline
from zenml.steps import Output, step


@pipeline
def artifact_visualization_pipeline(
    get_image, get_csv, get_markdown, get_html, get_html_large
):
    get_image()
    get_csv()
    get_markdown()
    get_html()
    get_html_large()


@step
def get_image() -> Output(image=Image.Image):
    return Image.open("docs/mkdocs/_assets/favicon.png")


@step
def get_markdown() -> Output(markdown=str):
    return "# Hello I am markdown\n\n## I am a header\n\nI am a paragraph"


@step
def get_html() -> Output(html=str):
    return "<html><body><h1>Hello I am HTML</h1></body></html>"


@step
def get_html_large() -> Output(html_large=str):
    return "<html><body><h1>Hello I am HTML</h1></body></html>"


@step
def get_csv() -> Output(csv=str):
    return "a,b,c\n1,2,3"


def main():
    pip = artifact_visualization_pipeline(
        get_image=get_image(),
        get_csv=get_csv(),
        get_markdown=get_markdown(),
        get_html=get_html(),
        get_html_large=get_html_large(),
    )
    pip.configure(enable_cache=False)
    pip.run()


if __name__ == "__main__":
    main()
