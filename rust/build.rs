//! Build script to embed the ZenML version from src/zenml/VERSION
//!
//! This ensures the Rust binary always reports the same version as the Python package.

use std::fs;
use std::path::Path;

fn main() {
    // Tell Cargo to rerun this build script if VERSION changes
    println!("cargo:rerun-if-changed=../src/zenml/VERSION");

    // Read the version file
    let version_path = Path::new(env!("CARGO_MANIFEST_DIR")).join("../src/zenml/VERSION");
    let version = fs::read_to_string(&version_path)
        .unwrap_or_else(|e| panic!("Failed to read VERSION file at {:?}: {}", version_path, e));

    // Set as environment variable for compile-time inclusion
    println!("cargo:rustc-env=ZENML_VERSION={}", version.trim());
}
