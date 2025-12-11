#!/usr/bin/env bash
# Runs all agent framework examples under examples/agent_framework_integrations
# Each example is executed in its own fresh uv virtual environment.
# Aggregates successes and failures, writes a summary and sets GitHub Actions outputs.

set -uo pipefail
shopt -s nullglob

log() {
  # UTC timestamped logs for easier debugging across timezones
  echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] $*"
}

# Resolve repository root from this script's location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
EXAMPLES_DIR="$ROOT_DIR/examples/agent_framework_integrations"

# Ensure uv is installed and available on PATH
if ! command -v uv >/dev/null 2>&1; then
  log "ERROR: 'uv' not found in PATH. Please install uv before running this script."
  exit 1
fi

# Validate examples directory exists
if [[ ! -d "$EXAMPLES_DIR" ]]; then
  log "ERROR: Examples directory not found at: $EXAMPLES_DIR"
  exit 1
fi

# Optional: allow forcing a specific Python version for the venvs via env var
# If unset, uv will select the current interpreter configured on the runner.
PYTHON_VERSION="${PYTHON_VERSION:-}"

# Arrays to track results
declare -a SUCCESSES=()
declare -a FAILURES=()
declare -a SKIPPED=()
declare -A DURATIONS_S=()  # name -> duration seconds

TOTAL_START_SEC="$(date +%s)"

# Create an output directory for logs (optional for debugging)
LOGS_DIR="$ROOT_DIR/agent-examples-logs"
mkdir -p "$LOGS_DIR"

# Detect if OPENAI_API_KEY is present without printing it
if [[ -n "${OPENAI_API_KEY:-}" ]]; then
  log "Environment check: OPENAI_API_KEY is set (value hidden)."
else
  log "WARNING: OPENAI_API_KEY is not set. Some examples may fail due to missing credentials."
fi

run_example() {
  local example_dir="$1"
  local name
  name="$(basename "$example_dir")"
  local log_file="$LOGS_DIR/${name}.log"

  log "Preparing to run example: ${name}"
  local start_sec end_sec duration_sec
  start_sec="$(date +%s)"

  # Guard: must have run.py and requirements.txt
  if [[ ! -f "$example_dir/run.py" || ! -f "$example_dir/requirements.txt" ]]; then
    log "Skipping '${name}' (missing run.py and/or requirements.txt)"
    SKIPPED+=("$name")
    return 0
  fi

  # Group logs in GitHub Actions UI for readability
  echo "::group::[${name}] Setup, install, and run"

  pushd "$example_dir" >/dev/null || {
    log "ERROR: Unable to enter directory: $example_dir"
    FAILURES+=("$name")
    echo "::endgroup::"
    return 0
  }

  # Always start with a fresh environment to avoid cross-example contamination
  rm -rf .venv || true

  # Create the virtual environment
  if [[ -n "$PYTHON_VERSION" ]]; then
    log "Creating uv venv with Python ${PYTHON_VERSION} for '${name}'" | tee -a "$log_file"
    if ! uv venv --python "$PYTHON_VERSION" >>"$log_file" 2>&1; then
      log "uv venv --python ${PYTHON_VERSION} failed for '${name}', falling back to 'uv venv'." | tee -a "$log_file"
      if ! uv venv >>"$log_file" 2>&1; then
        log "ERROR: Failed to create uv venv for '${name}'"
        popd >/dev/null || true
        FAILURES+=("$name")
        echo "::endgroup::"
        return 0
      fi
    fi
  else
    log "Creating uv venv for '${name}'" | tee -a "$log_file"
    if ! uv venv >>"$log_file" 2>&1; then
      log "ERROR: Failed to create uv venv for '${name}'"
      popd >/dev/null || true
      FAILURES+=("$name")
      echo "::endgroup::"
      return 0
    fi
  fi

  # Activate the environment
  # shellcheck disable=SC1091
  if ! source .venv/bin/activate; then
    log "ERROR: Failed to activate virtual environment for '${name}'"
    popd >/dev/null || true
    FAILURES+=("$name")
    echo "::endgroup::"
    return 0
  fi

  # Show Python and uv versions for traceability
  {
    echo "Python: $(python --version 2>&1)"
    echo "uv: $(uv --version 2>&1 || true)"
    echo "Pip (uv pip): $(uv pip --version 2>&1 || true)"
  } >>"$log_file" 2>&1

  # Install local zenml (editable) AND example requirements in a single resolution pass.
  # This ensures uv sees all constraints together and fails fast on conflicts
  # (e.g., if an example's dependency pins an incompatible version of a ZenML dep).
  log "Installing local zenml (editable) + requirements for '${name}'" | tee -a "$log_file"
  if ! uv pip install -e "$ROOT_DIR" -r requirements.txt >>"$log_file" 2>&1; then
    log "ERROR: Dependency installation failed for '${name}' (check for version conflicts)"
    deactivate >/dev/null 2>&1 || true
    popd >/dev/null || true
    FAILURES+=("$name")
    echo "::endgroup::"
    return 0
  fi

  # Execute the example
  log "Running run.py for '${name}'" | tee -a "$log_file"
  # Prepend repo src/ to PYTHONPATH to ensure local zenml code is import-preferred
  if PYTHONPATH="$ROOT_DIR/src:$PWD:${PYTHONPATH:-}" python -X utf8 run.py >>"$log_file" 2>&1; then
    log "SUCCESS: Example '${name}' completed."
    SUCCESSES+=("$name")
  else
    log "FAILURE: Example '${name}' failed. See log: $log_file"
    FAILURES+=("$name")
  fi

  # Cleanup and timing
  deactivate >/dev/null 2>&1 || true
  popd >/dev/null || true
  echo "::endgroup::"

  end_sec="$(date +%s)"
  duration_sec=$(( end_sec - start_sec ))
  DURATIONS_S["$name"]="$duration_sec"
}

# Discover and run all examples
for d in "$EXAMPLES_DIR"/*; do
  [[ -d "$d" ]] || continue
  run_example "$d"
done

TOTAL_END_SEC="$(date +%s)"
TOTAL_DURATION_S=$(( TOTAL_END_SEC - TOTAL_START_SEC ))

# Compose summary and failure list files at repository root
SUMMARY_FILE="$ROOT_DIR/agent-examples.summary.md"
DISCORD_SUMMARY_FILE="$ROOT_DIR/agent-examples.discord.md"
FAILURES_FILE="$ROOT_DIR/agent-examples.failures.txt"

PASS_COUNT="${#SUCCESSES[@]}"
FAIL_COUNT="${#FAILURES[@]}"
SKIP_COUNT="${#SKIPPED[@]}"
TOTAL_COUNT=$(( PASS_COUNT + FAIL_COUNT + SKIP_COUNT ))

{
  echo "# Agent Examples Test Report"
  echo
  echo "- Total discovered: ${TOTAL_COUNT}"
  echo "- Passed: ${PASS_COUNT}"
  echo "- Failed: ${FAIL_COUNT}"
  echo "- Skipped: ${SKIP_COUNT}"
  echo "- Total duration: ${TOTAL_DURATION_S}s"
  echo
  if (( PASS_COUNT > 0 )); then
    echo "## ✅ Passed"
    for n in "${SUCCESSES[@]}"; do
      d="${DURATIONS_S[$n]:-0}"
      echo "- ${n} (${d}s)"
    done
    echo
  fi
  if (( FAIL_COUNT > 0 )); then
    echo "## ❌ Failed"
    for n in "${FAILURES[@]}"; do
      d="${DURATIONS_S[$n]:-0}"
      echo "- ${n} (${d}s) — see agent-examples-logs/${n}.log"
    done
    echo
  fi
  if (( SKIP_COUNT > 0 )); then
    echo "## ⏭️ Skipped"
    for n in "${SKIPPED[@]}"; do
      echo "- ${n}"
    done
    echo
  fi
  echo "## Notes"
  echo "- Each example ran in an isolated uv virtual environment."
  echo "- OPENAI_API_KEY detected: $([[ -n "${OPENAI_API_KEY:-}" ]] && echo "yes" || echo "no")"
  echo "- Local zenml installed via editable install from this repository."
  echo "- Logs for each run are stored under agent-examples-logs/."
  echo
  echo "## Re-run a specific example locally"
  echo "\\\`\\\`\\\`bash"
  echo "cd examples/agent_framework_integrations/<example-name>"
  echo "${PYTHON_VERSION:+PYTHON_VERSION=${PYTHON_VERSION} }uv venv ${PYTHON_VERSION:+--python ${PYTHON_VERSION}}"
  echo "source .venv/bin/activate"
  echo "uv pip install -e \"$ROOT_DIR\" -r requirements.txt"
  echo "PYTHONPATH=\"$ROOT_DIR/src:\\\$PWD:\\\${PYTHONPATH:-}\" python run.py"
  echo "\\\`\\\`\\\`"
} >"$SUMMARY_FILE"

# Generate concise Discord summary
{
  if (( FAIL_COUNT > 0 )); then
    echo "**Failed Examples:**"
    for n in "${FAILURES[@]}"; do
      echo "• ${n}"
    done
  else
    echo "All agent examples passed! ✅"
  fi
} >"$DISCORD_SUMMARY_FILE"

# Write failures file (newline-separated). Create empty file if none failed for consistent artifacts.
: >"$FAILURES_FILE"
if (( FAIL_COUNT > 0 )); then
  for n in "${FAILURES[@]}"; do
    echo "$n" >>"$FAILURES_FILE"
  done
fi

# Emit GitHub Actions outputs if available
if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  # CSV lists for convenience
  FAIL_LIST=""
  PASS_LIST=""
  SKIP_LIST=""
  if (( FAIL_COUNT > 0 )); then
    FAIL_LIST="$(IFS=, ; echo "${FAILURES[*]}")"
  fi
  if (( PASS_COUNT > 0 )); then
    PASS_LIST="$(IFS=, ; echo "${SUCCESSES[*]}")"
  fi
  if (( SKIP_COUNT > 0 )); then
    SKIP_LIST="$(IFS=, ; echo "${SKIPPED[*]}")"
  fi

  {
    echo "fail_count=${FAIL_COUNT}"
    echo "fail_list=${FAIL_LIST}"
    echo "pass_count=${PASS_COUNT}"
    echo "pass_list=${PASS_LIST}"
    echo "skip_count=${SKIP_COUNT}"
    echo "skip_list=${SKIP_LIST}"
    echo "total_count=${TOTAL_COUNT}"
    echo "total_duration_s=${TOTAL_DURATION_S}"
    echo "summary_file=${SUMMARY_FILE}"
    echo "discord_summary_file=${DISCORD_SUMMARY_FILE}"
    echo "failures_file=${FAILURES_FILE}"
    echo "logs_dir=${LOGS_DIR}"
  } >>"$GITHUB_OUTPUT"
fi

# Always exit 0. The workflow will decide whether to fail the job based on outputs.
log "All examples processed. Passed: ${PASS_COUNT}, Failed: ${FAIL_COUNT}, Skipped: ${SKIP_COUNT}."
exit 0