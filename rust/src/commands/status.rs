use serde_yaml::Value;
use std::env;
use std::fs;
use std::io::{self, Write};
use std::path::{Path, PathBuf};

const REPO_MARKER_DIR: &str = ".zen";
const GLOBAL_CONFIG_FILE: &str = "config.yaml";
const LOCAL_STORES_DIR: &str = "local_stores";

const ENV_REPOSITORY_PATH: &str = "ZENML_REPOSITORY_PATH";
const ENV_CONFIG_PATH: &str = "ZENML_CONFIG_PATH";
const ENV_LOCAL_STORES_PATH: &str = "ZENML_LOCAL_STORES_PATH";

pub(crate) fn find_repo_root() -> Option<PathBuf> {
    if let Ok(override_path) = env::var(ENV_REPOSITORY_PATH) {
        if !override_path.is_empty() {
            return Some(PathBuf::from(override_path));
        }
    }

    let mut current = env::current_dir().ok()?;
    loop {
        if current.join(REPO_MARKER_DIR).is_dir() {
            return Some(current);
        }
        if !current.pop() {
            break;
        }
    }
    None
}

pub(crate) fn get_global_config_directory() -> Option<PathBuf> {
    if let Ok(override_path) = env::var(ENV_CONFIG_PATH) {
        if !override_path.is_empty() {
            return Some(PathBuf::from(override_path));
        }
    }

    dirs::config_dir().map(|dir| dir.join("zenml"))
}

pub fn print_status() -> io::Result<()> {
    let repo_root = find_repo_root();
    let config_dir = get_global_config_directory();
    let local_stores_path = get_local_stores_path(config_dir.as_deref());
    let (active_stack_id, active_project_id) = read_active_ids(config_dir.as_deref());

    let mut stdout = io::stdout();
    writeln!(stdout, "-----ZenML Status-----")?;

    match repo_root {
        Some(path) => writeln!(stdout, "Repository root: {}", path.display())?,
        None => writeln!(stdout, "Repository root: Not in a ZenML repository")?,
    }

    match &config_dir {
        Some(path) => writeln!(stdout, "Config directory: {}", path.display())?,
        None => writeln!(stdout, "Config directory: Not set")?,
    }

    match local_stores_path {
        Some(path) => writeln!(stdout, "Local stores: {}", path.display())?,
        None => writeln!(stdout, "Local stores: Not set")?,
    }

    match active_stack_id {
        Some(id) => writeln!(stdout, "Active stack ID: {}", id)?,
        None => writeln!(stdout, "Active stack ID: Not set")?,
    }

    match active_project_id {
        Some(id) => writeln!(stdout, "Active project ID: {}", id)?,
        None => writeln!(stdout, "Active project ID: Not set")?,
    }

    Ok(())
}

fn get_local_stores_path(config_dir: Option<&Path>) -> Option<PathBuf> {
    if let Ok(override_path) = env::var(ENV_LOCAL_STORES_PATH) {
        if !override_path.is_empty() {
            return Some(PathBuf::from(override_path));
        }
    }

    config_dir.map(|dir| dir.join(LOCAL_STORES_DIR))
}

fn read_active_ids(config_dir: Option<&Path>) -> (Option<String>, Option<String>) {
    let config_dir = match config_dir {
        Some(dir) => dir,
        None => return (None, None),
    };

    let config_path = config_dir.join(GLOBAL_CONFIG_FILE);
    let contents = match fs::read_to_string(&config_path) {
        Ok(contents) => contents,
        Err(_) => return (None, None),
    };

    let yaml: Value = match serde_yaml::from_str(&contents) {
        Ok(value) => value,
        Err(_) => return (None, None),
    };

    let active_stack_id = yaml
        .get("active_stack_id")
        .and_then(Value::as_str)
        .map(|value| value.to_string());

    let active_project_id = yaml
        .get("active_project_id")
        .and_then(Value::as_str)
        .map(|value| value.to_string());

    (active_stack_id, active_project_id)
}