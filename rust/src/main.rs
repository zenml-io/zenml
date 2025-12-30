//! ZenML CLI - Fast Rust entry point with Python fallback
//!
//! This binary provides a fast entry point for the ZenML CLI. It handles simple
//! commands (version, help) natively in Rust for instant response, and delegates
//! all other commands to the Python CLI.
//!
//! Architecture:
//! - Fast path: `--version`, `-v`, `version`, root `--help` → handled in Rust
//! - Slow path: Everything else → delegates to Python `zenml_cli` module

use rand::seq::SliceRandom;
use std::env;
use std::io::{self, IsTerminal, Write};
use std::process::{Command, ExitCode};

/// Version embedded at build time from src/zenml/VERSION
const VERSION: &str = env!("ZENML_VERSION");

/// ASCII art banners matching the Python CLI (src/zenml/cli/version.py)
const ASCII_ARTS: [&str; 5] = [
    r#"      
       .-') _   ('-.       .-') _  _   .-')              
      (  OO) )_(  OO)     ( OO ) )( '.( OO )_            
    ,(_)----.(,------.,--./ ,--,'  ,--.   ,--.),--.      
    |       | |  .---'|   \ |  |\  |   `.'   | |  |.-')  
    '--.   /  |  |    |    \|  | ) |         | |  | OO ) 
    (_/   /  (|  '--. |  .     |/  |  |'.'|  | |  |`-' | 
     /   /___ |  .--' |  |\    |   |  |   |  |(|  '---.' 
    |        ||  `---.|  | \   |   |  |   |  | |      |  
    `--------'`------'`--'  `--'   `--'   `--' `------' 
    "#,
    r#"
      ____..--'     .-''-.   ,---.   .--. ,---.    ,---.   .---.      
     |        |   .'_ _   \  |    \  |  | |    \  /    |   | ,_|      
     |   .-'  '  / ( ` )   ' |  ,  \ |  | |  ,  \/  ,  | ,-./  )      
     |.-'.'   / . (_ o _)  | |  |\_ \|  | |  |\_   /|  | \  '_ '`)    
        /   _/  |  (_,_)___| |  _( )_\  | |  _( )_/ |  |  > (_)  )    
      .'._( )_  '  \   .---. | (_ o _)  | | (_ o _) |  | (  .  .-'    
    .'  (_'o._)  \  `-'    / |  (_,_)\  | |  (_,_)  |  |  `-'`-'|___  
    |    (_,_)|   \       /  |  |    |  | |  |      |  |   |        \ 
    |_________|    `'-..-'   '--'    '--' '--'      '--'   `--------`                                                           
    "#,
    r#"
     ________                      __       __  __       
    |        \                    |  \     /  \|  \      
     \$$$$$$$$  ______   _______  | $$\   /  $$| $$      
        /  $$  /      \ |       \ | $$$\ /  $$$| $$      
       /  $$  |  $$$$$$\| $$$$$$$\| $$$$\  $$$$| $$      
      /  $$   | $$    $$| $$  | $$| $$\$$ $$ $$| $$      
     /  $$___ | $$$$$$$$| $$  | $$| $$ \$$$| $$| $$_____ 
    |  $$    \ \$$     \| $$  | $$| $$  \$ | $$| $$     \
     \$$$$$$$$  \$$$$$$$ \$$   \$$ \$$      \$$ \$$$$$$$$
    "#,
    r#"
        )                    *      (     
     ( /(                  (  `     )\ )  
     )\())    (            )\))(   (()/(  
    ((_)\    ))\    (     ((_)()\   /(_)) 
     _((_)  /((_)   )\ )  (_()((_) (_))   
    |_  /  (_))    _(_/(  |  \/  | | |    
     / /   / -_)  | ' \)) | |\/| | | |__  
    /___|  \___|  |_||_|  |_|  |_| |____| 
    "#,
    r#"
███████ ███████ ███    ██ ███    ███ ██      
   ███  ██      ████   ██ ████  ████ ██      
  ███   █████   ██ ██  ██ ██ ████ ██ ██      
 ███    ██      ██  ██ ██ ██  ██  ██ ██      
███████ ███████ ██   ████ ██      ██ ███████ 
    "#,
];

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

/// Print Click-style version output: "zenml, version X.Y.Z"
fn print_version_flag() -> io::Result<()> {
    // Match Click's version_option format
    writeln!(io::stderr(), "zenml, version {}", VERSION)
}

/// Print the `zenml version` command output with ASCII art banner
fn print_version_command() -> io::Result<()> {
    let mut rng = rand::thread_rng();
    let banner = ASCII_ARTS.choose(&mut rng).unwrap_or(&ASCII_ARTS[0]);

    let stderr = io::stderr();
    let mut handle = stderr.lock();

    // Print the ASCII art banner
    writeln!(handle, "{}", banner)?;

    // Print version with bold formatting if terminal supports it
    if io::stderr().is_terminal() {
        // ANSI bold: \x1b[1m ... \x1b[0m
        writeln!(handle, "\x1b[1mversion: {}\x1b[0m", VERSION)
    } else {
        writeln!(handle, "version: {}", VERSION)
    }
}

/// Print root help text
/// For Phase 1, we delegate to Python to get the full Click-generated help
fn print_help_root() -> io::Result<ExitCode> {
    // For now, delegate to Python to get accurate help text
    // This ensures we match Click's formatted output exactly
    delegate_to_python(&["--help".to_string()])
}

/// Delegate command execution to the Python CLI
fn delegate_to_python(args: &[String]) -> io::Result<ExitCode> {
    // Build the Python command
    // We use `python -c` to invoke the CLI directly without needing __main__.py
    let python_code = r#"
import sys
from zenml_cli import cli
sys.exit(cli.main(args=sys.argv[1:], prog_name='zenml', standalone_mode=False) or 0)
"#;

    // Find Python executable
    let python = find_python()?;

    // Build command: python -c "..." <args>
    let mut cmd = Command::new(&python);
    cmd.arg("-c").arg(python_code);
    cmd.args(args);

    // Execute and wait for completion
    let status = cmd.status().map_err(|e| {
        io::Error::new(
            e.kind(),
            format!(
                "Failed to execute Python CLI via '{}': {}. \
                 Make sure Python is installed and zenml is in your Python path.",
                python, e
            ),
        )
    })?;

    Ok(if status.success() {
        ExitCode::SUCCESS
    } else {
        ExitCode::from(status.code().unwrap_or(1) as u8)
    })
}

/// Find the Python executable to use
fn find_python() -> io::Result<String> {
    // Check for explicit override
    if let Ok(python) = env::var("ZENML_PYTHON") {
        return Ok(python);
    }

    // Try common Python executable names
    for name in &["python3", "python"] {
        if Command::new(name)
            .arg("--version")
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false)
        {
            return Ok(name.to_string());
        }
    }

    Err(io::Error::new(
        io::ErrorKind::NotFound,
        "Could not find Python executable. Tried 'python3' and 'python'. \
         Set ZENML_PYTHON environment variable to specify the Python interpreter.",
    ))
}

fn main() -> ExitCode {
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
        assert_eq!(
            classify_args(&["zenml".into()]),
            CliAction::HelpRoot
        );
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
