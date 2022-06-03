from click.testing import CliRunner

from zenml.cli.served_models import served_models

runner = CliRunner()
result = runner.invoke(
    served_models, ["describe", "b1baa753-5e5c-4132-b2d8-0c9773c04b5c"]
)
