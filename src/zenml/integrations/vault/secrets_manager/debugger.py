from click.testing import CliRunner

from zenml.cli.secret import secret

runner = CliRunner()
result = runner.invoke(secret, ["get", "aria"])
