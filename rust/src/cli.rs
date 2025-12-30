//! ZenML CLI - Fast Rust entry point with Python fallback
//!
//! This module provides a fast entry point for the ZenML CLI. It handles simple
//! commands (version, help) natively in Rust for instant response, and delegates
//! all other commands to the Python CLI.
//!
//! Architecture:
//! - Fast path: `--version`, `-v`, `version`, root `--help` → handled in Rust
//! - Slow path: Everything else → delegates to Python `zenml_cli` module

use std::env;
use std::process::ExitCode;

use crate::commands::help::print_help_root;
use crate::commands::version::{print_version_command, print_version_flag};
use crate::python_bridge::delegate_to_python;

/// Classifies CLI arguments to determine fast path vs delegation
#[derive(Debug, PartialEq)]
enum CliAction {
    /// --version or -v flag (Click-style version output)
    VersionFlag,
    /// `zenml version` subcommand (banner + version)
    VersionCommand,
    /// Root --help with no subcommand
    HelpRoot,
    /// Delegate to Python CLI
    Delegate,
}

/// Parse arguments and determine the appropriate action
fn classify_args(args: &[String]) -> CliAction {
    // Skip the program name (args[0])
    let args: Vec<&str> = args.iter().skip(1).map(|s| s.as_str()).collect();

    match args.as_slice() {
        // Empty args or just flags we handle
        [] => CliAction::HelpRoot,
        ["--help"] | ["-h"] => CliAction::HelpRoot,
        ["--version"] | ["-v"] => CliAction::VersionFlag,
        ["version"] => CliAction::VersionCommand,
        // Version flag can appear anywhere (Click behavior)
        _ if args.contains(&"--version") || args.contains(&"-v") => CliAction::VersionFlag,
        // Everything else delegates to Python
        _ => CliAction::Delegate,
    }
}

/// Run the CLI entrypoint with a fast-path for simple commands.
pub fn run() -> ExitCode {
    // Check for explicit Python CLI override (escape hatch)
    if env::var("ZENML_USE_PYTHON_CLI").is_ok() {
        let args: Vec<String> = env::args().skip(1).collect();
        return match delegate_to_python(&args) {
            Ok(code) => code,
            Err(e) => {
                eprintln!("Error: {}", e);
                ExitCode::FAILURE
            }
        };
    }

    // Collect arguments
    let args: Vec<String> = env::args().collect();

    // Classify and handle
    match classify_args(&args) {
        CliAction::VersionFlag => {
            if let Err(e) = print_version_flag() {
                eprintln!("Error printing version: {}", e);
                return ExitCode::FAILURE;
            }
            ExitCode::SUCCESS
        }
        CliAction::VersionCommand => {
            if let Err(e) = print_version_command() {
                eprintln!("Error printing version: {}", e);
                return ExitCode::FAILURE;
            }
            ExitCode::SUCCESS
        }
        CliAction::HelpRoot => match print_help_root() {
            Ok(code) => code,
            Err(e) => {
                eprintln!("Error: {}", e);
                ExitCode::FAILURE
            }
        },
        CliAction::Delegate => {
            let args: Vec<String> = env::args().skip(1).collect();
            match delegate_to_python(&args) {
                Ok(code) => code,
                Err(e) => {
                    eprintln!("Error: {}", e);
                    ExitCode::FAILURE
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_classify_version_flag() {
        assert_eq!(
            classify_args(&["zenml".into(), "--version".into()]),
            CliAction::VersionFlag
        );
        assert_eq!(
            classify_args(&["zenml".into(), "-v".into()]),
            CliAction::VersionFlag
        );
    }

    #[test]
    fn test_classify_version_command() {
        assert_eq!(
            classify_args(&["zenml".into(), "version".into()]),
            CliAction::VersionCommand
        );
    }

    #[test]
    fn test_classify_help() {
        assert_eq!(
            classify_args(&["zenml".into(), "--help".into()]),
            CliAction::HelpRoot
        );
        assert_eq!(classify_args(&["zenml".into()]), CliAction::HelpRoot);
    }

    #[test]
    fn test_classify_delegate() {
        assert_eq!(
            classify_args(&["zenml".into(), "stack".into(), "list".into()]),
            CliAction::Delegate
        );
        assert_eq!(
            classify_args(&["zenml".into(), "pipeline".into(), "run".into()]),
            CliAction::Delegate
        );
    }

    #[test]
    fn test_version_flag_anywhere() {
        // Click allows --version anywhere in args
        assert_eq!(
            classify_args(&["zenml".into(), "stack".into(), "--version".into()]),
            CliAction::VersionFlag
        );
    }
}