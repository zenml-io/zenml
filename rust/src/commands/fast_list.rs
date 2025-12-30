//! Fast-path list commands using PyO3 to call Python Client API directly.
//!
//! This module bypasses the heavy CLI import chain by calling a minimal
//! Python helper that uses Click for parsing and Client() for data fetching.

use pyo3::prelude::*;
use pyo3::types::PyList;
use std::process::ExitCode;

/// Error type for fast list operations
#[derive(Debug)]
pub enum FastListError {
    /// PyO3/Python error occurred
    Python(String),
}

impl std::fmt::Display for FastListError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            FastListError::Python(msg) => write!(f, "Python error: {}", msg),
        }
    }
}

impl std::error::Error for FastListError {}

impl From<PyErr> for FastListError {
    fn from(err: PyErr) -> Self {
        FastListError::Python(err.to_string())
    }
}

/// Set up Python path for the embedded interpreter.
///
/// PyO3's embedded Python may not correctly recognize virtual environments,
/// causing `sys.prefix` to point to the base Python instead of the venv.
/// This function uses environment variables (VIRTUAL_ENV, CONDA_PREFIX) to
/// find and add the correct site-packages directory.
fn setup_python_path(py: Python<'_>) -> PyResult<()> {
    let sys = py.import("sys")?;
    let site = py.import("site")?;
    
    // Get Python version for constructing site-packages path
    let major: i32 = sys.getattr("version_info")?.getattr("major")?.extract()?;
    let minor: i32 = sys.getattr("version_info")?.getattr("minor")?.extract()?;
    
    // Debug output if requested
    if std::env::var("ZENML_DEBUG_PYTHON").is_ok() {
        let prefix: String = sys.getattr("prefix")?.extract()?;
        let base_prefix: String = sys.getattr("base_prefix")?.extract()?;
        let sys_path: Vec<String> = sys.getattr("path")?.extract()?;
        eprintln!("DEBUG: sys.prefix = {}", prefix);
        eprintln!("DEBUG: sys.base_prefix = {}", base_prefix);
        eprintln!("DEBUG: sys.path (before) = {:?}", sys_path);
    }
    
    // Try to find venv root from environment variables
    // Priority: VIRTUAL_ENV (venv/pyenv) > CONDA_PREFIX (conda)
    let venv_root = std::env::var("VIRTUAL_ENV")
        .or_else(|_| std::env::var("CONDA_PREFIX"))
        .ok();
    
    if let Some(venv) = &venv_root {
        // Construct the venv's site-packages path
        let venv_site_packages = format!("{}/lib/python{}.{}/site-packages", venv, major, minor);
        
        if std::env::var("ZENML_DEBUG_PYTHON").is_ok() {
            eprintln!("DEBUG: Adding venv site-packages: {}", venv_site_packages);
        }
        
        // Use site.addsitedir() which properly handles .pth files
        site.call_method1("addsitedir", (&venv_site_packages,))?;
    }
    
    // Add PYTHONPATH entries (for editable installs like zenml src/)
    if let Ok(pythonpath) = std::env::var("PYTHONPATH") {
        let sys_path = sys.getattr("path")?;
        for path in pythonpath.split(':') {
            if !path.is_empty() {
                sys_path.call_method1("insert", (0, path))?;
            }
        }
    }
    
    if std::env::var("ZENML_DEBUG_PYTHON").is_ok() {
        let sys_path: Vec<String> = sys.getattr("path")?.extract()?;
        eprintln!("DEBUG: sys.path (after) = {:?}", sys_path);
    }
    
    Ok(())
}

/// Run the fast-path stack list command via PyO3.
///
/// Calls `zenml.cli.fast_list.run_stack_list(argv)` which uses Click
/// for argument parsing and Client().list_stacks() for data fetching.
///
/// # Arguments
/// * `args` - Command-line arguments after "stack list"
///
/// # Returns
/// * `Ok(ExitCode)` - The exit code from Python
/// * `Err(FastListError)` - If PyO3 initialization or call fails
pub fn run_stack_list(args: Vec<String>) -> Result<ExitCode, FastListError> {
    Python::with_gil(|py| {
        // Ensure Python path is set up correctly for virtual environment
        setup_python_path(py)?;
        
        // Import the fast_list module
        let fast_list = py.import("zenml.cli.fast_list")?;
        
        // Convert Rust Vec<String> to Python list
        let py_args = PyList::new(py, &args)?;
        
        // Call run_stack_list(argv) and get exit code
        let result = fast_list.call_method1("run_stack_list", (py_args,))?;
        let exit_code: i32 = result.extract()?;
        
        Ok(ExitCode::from(exit_code as u8))
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_fast_list_error_display() {
        let err = FastListError::Python("test error".to_string());
        assert!(err.to_string().contains("test error"));
    }
}
