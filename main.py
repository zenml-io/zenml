from bentoml import bentos
from bentoml.serve import serve_http_development

if __name__ == "__main__":
    serve_http_development(
        "pytorch_mnist_demo:kvqb7cc4qso2smup",
        working_dir="/Users/safoine-zenml/work-dir/bentomlPR/zenml/examples/bentoml_deployment",
        port=3001,
    )
    breakpoint()