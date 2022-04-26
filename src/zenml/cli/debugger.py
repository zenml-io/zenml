from click.testing import CliRunner

from zenml.cli.cli import cli

runner = CliRunner()
result = runner.invoke(cli)
