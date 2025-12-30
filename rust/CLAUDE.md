# ZenML Rust CLI Development Notes

## PyO3 Virtual Environment Handling

### The Problem

When PyO3 embeds Python, **the embedded interpreter does NOT automatically recognize virtual environments**. Specifically:

- `sys.prefix` and `sys.base_prefix` both point to the **base Python installation**, not the virtualenv
- This means packages installed in the virtualenv (like `rich`, `click`, etc.) are NOT found
- This happens even when the Rust binary was compiled against the virtualenv's Python

**Example debug output showing the issue:**
```
DEBUG: sys.prefix = /Users/user/.pyenv/versions/3.12.5  # Wrong! Should be venv path
DEBUG: sys.base_prefix = /Users/user/.pyenv/versions/3.12.5
DEBUG: sys.path = [...base Python site-packages only...]
```

### The Solution

Use environment variables to find the virtualenv root at runtime:

1. **`VIRTUAL_ENV`** - Set by venv, pyenv-virtualenv, and most virtualenv tools
2. **`CONDA_PREFIX`** - Set by conda environments

Then construct the site-packages path and add it using `site.addsitedir()`:

```rust
let venv_root = std::env::var("VIRTUAL_ENV")
    .or_else(|_| std::env::var("CONDA_PREFIX"))
    .ok();

if let Some(venv) = &venv_root {
    let venv_site_packages = format!("{}/lib/python{}.{}/site-packages", 
        venv, major, minor);
    site.call_method1("addsitedir", (&venv_site_packages,))?;
}
```

### Why This Works

- `VIRTUAL_ENV` is reliably set when a virtualenv is activated
- `site.addsitedir()` properly handles `.pth` files (for editable installs)
- This approach is runtime-based, so it works across different developer environments

### Alternative: PyConfig (More Complex)

For a cleaner but more complex solution, use `PyConfig` to set `home` before interpreter initialization:

```rust
// Set PyConfig.home to the venv root
// Python will then compute correct sys.prefix and sys.path
```

This requires removing `auto-initialize` from PyO3 features and handling initialization manually.

### Testing

Set `ZENML_DEBUG_PYTHON=1` to see debug output:

```bash
ZENML_DEBUG_PYTHON=1 VIRTUAL_ENV="/path/to/venv" ./rust/target/release/zenml stack list
```

### Benchmark Results (Phase 3b)

| Command | Fast Path (PyO3) | Python CLI (subprocess) | Speedup |
|---------|------------------|-------------------------|---------|
| `stack list` | ~5.8s | ~6.9s | ~15% |

Note: Most time is spent on network calls to the server. The import chain savings (~1s) are meaningful but represent a smaller portion of total time than expected.

## Building

```bash
cd rust
cargo build --release
```

The binary is at `rust/target/release/zenml`.

## Architecture

```
rust/src/
├── main.rs           # Entry point
├── cli.rs            # CliAction enum, classify_args(), run()
├── python_bridge.rs  # subprocess delegation (fallback)
└── commands/
    ├── mod.rs
    ├── version.rs    # Pure Rust (450x speedup)
    ├── help.rs       # Pure Rust (520x speedup)
    ├── status.rs     # Pure Rust (300x+ speedup)
    ├── clean.rs      # Pure Rust
    └── fast_list.rs  # PyO3 bridge (~15% speedup)
```
