use std::env;
use std::fs;
use std::io::{self, Write};
use std::path::Path;

use crate::commands::status::{find_repo_root, get_global_config_directory};

const REPO_MARKER_DIR: &str = ".zen";
const ENV_LOCAL_STORES_PATH: &str = "ZENML_LOCAL_STORES_PATH";
const CLEAN_PROMPT: &str = "DANGER: This will delete all ZenML config. Continue? [y/N]";

pub fn run_clean(yes: bool, local: bool) -> io::Result<()> {
    if !yes && !confirm(CLEAN_PROMPT)? {
        return Ok(());
    }

    if let Some(repo_root) = find_repo_root() {
        let repo_marker = repo_root.join(REPO_MARKER_DIR);
        delete_path_if_exists(&repo_marker)?;
    }

    if !local && !has_local_stores_override() {
        if let Some(config_dir) = get_global_config_directory() {
            delete_path_if_exists(&config_dir)?;
        }
    }

    Ok(())
}

fn confirm(prompt: &str) -> io::Result<bool> {
    let mut stdout = io::stdout();
    write!(stdout, "{}", prompt)?;
    stdout.flush()?;

    let mut input = String::new();
    io::stdin().read_line(&mut input)?;

    let response = input.trim().to_ascii_lowercase();
    Ok(response == "y" || response == "yes")
}

// Use symlink_metadata to avoid deleting symlink targets outside the repo.
fn delete_path_if_exists(path: &Path) -> io::Result<()> {
    match fs::symlink_metadata(path) {
        Ok(meta) => {
            if meta.file_type().is_symlink() || meta.is_file() {
                fs::remove_file(path)?;
            } else if meta.is_dir() {
                fs::remove_dir_all(path)?;
            }
        }
        Err(err) if err.kind() == io::ErrorKind::NotFound => {}
        Err(err) => return Err(err),
    }

    Ok(())
}

fn has_local_stores_override() -> bool {
    env::var(ENV_LOCAL_STORES_PATH)
        .map(|value| !value.is_empty())
        .unwrap_or(false)
}