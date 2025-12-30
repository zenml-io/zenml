use std::io::{self, Write};
use std::process::ExitCode;

const ROOT_HELP: &str = r#"Usage: zenml [OPTIONS] COMMAND [ARGS]...

  CLI base command for ZenML.

Options:
  -v, --version  Show the version and exit.
  --help         Show this message and exit.

Available ZenML Commands (grouped):

  Stack Components:
      alerter                 Commands to interact with alerters.
      annotator               Commands to interact with annotators.
      artifact-store          Commands to interact with artifact stores.
      container-registry      Commands to interact with container registries.
      data-validator          Commands to interact with data validators.
      deployer                Commands to interact with deployers.
      experiment-tracker      Commands to interact with experiment trackers.
      feature-store           Commands to interact with feature stores.
      image-builder           Commands to interact with image builders.
      log-store               Commands to interact with log stores.
      model-deployer          Commands to interact with model deployers.
      model-registry          Commands to interact with model registries.
      orchestrator            Commands to interact with orchestrators.
      step-operator           Commands to interact with step operators.

  Integrations:
      integration             Interact with external integrations.

  Management Tools:
      analytics               Analytics for opt-in and opt-out.
      artifact                Commands for interacting with artifacts.
      authorized-device       Interact with authorized devices.
      code-repository         Interact with code repositories.
      deployment              Interact with deployments.
      logging                 Configuration of logging for ZenML pipelines.
      pipeline                Interact with pipelines, runs and schedules.
      project                 Commands for project management.
      server                  Commands for managing ZenML servers.
      stack                   Manage stacks.
      tag                     Interact with tags.

  Model Control Plane:
      model                   Interact with models and model versions in the Model
                              Control Plane.

  Identity and Security:
      secret                  Create, list, update, or delete secrets.
      service-account         Commands for service account management.
      service-connector       Configure and manage service connectors.
      user                    Commands for user management.

  Other Commands:
      connect                 Connect to a remote ZenML server.
      disconnect              Disconnect from a ZenML server.
      down                    Shut down the local ZenML dashboard.
      downgrade               Downgrade zenml version in global config.
      go                      Quickly explore ZenML with this walk-through.
      init                    Initialize a ZenML repository.
      login                   Login to a ZenML server.
      logout                  Log out from a ZenML server and optionally clear
                              stored credentials.
      logs                    Show the logs for the local ZenML server.
      show                    Show the ZenML dashboard.
      status                  Show information about the current configuration.
      up                      Start the ZenML dashboard locally.
      version                 Version of ZenML.
"#;

/// Print root help text
/// Use a static snapshot to match Click output without Python startup
pub fn print_help_root() -> io::Result<ExitCode> {
    io::stdout().write_all(ROOT_HELP.as_bytes())?;
    Ok(ExitCode::SUCCESS)
}