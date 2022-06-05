from click.testing import CliRunner

from zenml.cli.served_models import served_models

runner = CliRunner()
result = runner.invoke(served_models, ["list"])
