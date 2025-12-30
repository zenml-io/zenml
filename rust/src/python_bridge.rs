use std::env;
use std::io;
use std::process::{Command, ExitCode};

/// Delegate command execution to the Python CLI
pub fn delegate_to_python(args: &[String]) -> io::Result<ExitCode> {
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
pub fn find_python() -> io::Result<String> {
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