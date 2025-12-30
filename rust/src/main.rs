mod cli;
mod commands;
mod python_bridge;

use std::process::ExitCode;

fn main() -> ExitCode {
    cli::run()
}
