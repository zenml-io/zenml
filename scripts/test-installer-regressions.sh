#!/usr/bin/env bash
# Resolver and shell regressions use local wheels, real uv, and isolated paths.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INSTALLER="${1:-$ROOT/install-zenml.sh}"
PYTHON="$(uv python find --no-python-downloads '>=3.11,<3.14')"
"$PYTHON" - "$INSTALLER" "${2:-all}" "$BASH" <<'PY'
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

source = Path(sys.argv[1]).resolve()
selection = sys.argv[2]
root = Path(tempfile.mkdtemp(prefix="zenml-installer-regressions-"))
uv = shutil.which("uv")
assert uv
base = os.environ.copy()
for key in list(base):
    if key.startswith("ZENML_INSTALL_") or key in (
        "VIRTUAL_ENV", "UV_PYTHON", "UV_PROJECT_ENVIRONMENT", "UV_CONSTRAINT",
        "UV_FROZEN", "UV_NO_SYNC", "UV_INSTALL_DIR", "XDG_BIN_HOME", "UV_PROJECT", "UV_WORKING_DIR",
    ):
        base.pop(key)
base.update(
    UV_CACHE_DIR=str(root / "cache"), UV_PYTHON_DOWNLOADS="never",
    UV_OFFLINE="1", UV_NO_INDEX="1", UV_NO_CONFIG="1", UV_NO_CACHE="1", NO_COLOR="1",
    ZENML_ANALYTICS_OPT_IN="false",  # test installs must never report usage
)
base["UV_PYTHON_INSTALL_DIR"] = subprocess.check_output([uv, "python", "dir"], env=base, text=True).strip()
failures = []
passed = 0


def wheel(directory: Path, name: str, version: str, requires: str = ">=3.10,<3.15", dependencies: tuple[str, ...] = (), broken: bool = False) -> None:
    directory.mkdir(exist_ok=True, parents=True)
    dist = name.replace("-", "_")
    info = f"{dist}-{version}.dist-info"
    files = {
        f"{info}/METADATA": (
            f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n"
            f"Requires-Python: {requires}\nProvides-Extra: local\nProvides-Extra: server\n"
            + "".join(f"Requires-Dist: {dependency}\n" for dependency in dependencies)
        ),
        f"{info}/WHEEL": "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
    }
    if name == "zenml":
        body = 'raise SystemExit("broken fixture CLI")' if broken else 'from importlib.metadata import version; print("zenml, version " + version("zenml"))'
        files["zenml_fixture.py"] = f"def main():\n    {body}\n"
        files[f"{info}/entry_points.txt"] = "[console_scripts]\nzenml = zenml_fixture:main\n"
    files[f"{info}/RECORD"] = "".join(f"{path},,\n" for path in files)
    with zipfile.ZipFile(directory / f"{dist}-{version}-py3-none-any.whl", "w") as archive:
        for path, content in files.items():
            archive.writestr(path, content)


def fixture(label: str) -> tuple[Path, dict[str, str], Path]:
    directory = root / label
    directory.mkdir()
    env = base | {
        "TEST_HOME": str(directory / "home"),
        "UV_TOOL_DIR": str(directory / "tools"), "UV_TOOL_BIN_DIR": str(directory / "bin"),
        "XDG_CONFIG_HOME": str(directory / "config"), "XDG_DATA_HOME": str(directory / "data"),
        "XDG_CACHE_HOME": str(directory / "cache"), "ZENML_CONFIG_PATH": str(directory / "zenml"),
        "UV_FIND_LINKS": str(directory / "wheels"),
    }
    Path(env["TEST_HOME"]).mkdir()
    installer = directory / "install.sh"
    # Keep HOME unchanged: only this disposable production copy uses TEST_HOME.
    installer.write_text(source.read_text().replace("$HOME", "$TEST_HOME"))
    return directory, env, installer


def project(directory: Path, requires: str = ">=3.11,<3.15", dependencies: tuple[str, ...] = ()) -> None:
    directory.mkdir(exist_ok=True)
    (directory / "pyproject.toml").write_text(
        '[project]\nname = "installer-fixture"\nversion = "0.0.0"\n'
        f'requires-python = "{requires}"\ndependencies = {list(dependencies)!r}\n'
    )


def run(directory: Path, env: dict[str, str], installer: Path, *args: str, success: bool = True) -> str:
    result = subprocess.run(
        [sys.argv[3], str(installer), "--no-skills", *args],
        cwd=directory, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        timeout=60,
    )
    with (directory / "runs.log").open("a") as log:
        log.write(f"\n$ {' '.join(args)}\n{result.stdout}")
    assert (result.returncode == 0) == success, result.stdout
    return result.stdout


def read_version(executable: Path) -> str:
    return subprocess.check_output([str(executable), "--version"], text=True).strip().split()[-1]


def capped_project() -> None:
    directory, env, installer = fixture("capped")
    # CI installs both minors. A newest-only Python request must not escape <3.14.
    subprocess.run([uv, "python", "find", "--no-python-downloads", "3.14"], env=base, check=True, stdout=subprocess.DEVNULL)
    wheel(directory / "wheels", "zenml", "0.98.1")
    project(directory, ">=3.11,<3.14")
    before = (directory / "pyproject.toml").read_text().split("dependencies")[0]
    run(directory, env, installer, "--project", "--no-modify-path", "--extras=")
    actual = subprocess.check_output([str(directory / ".venv/bin/python"), "-c", "import sys; print(sys.version_info.minor)"], text=True)
    assert 11 <= int(actual) < 14, actual
    assert (directory / "pyproject.toml").read_text().split("dependencies")[0] == before
    assert not (directory / ".python-version").exists()


def incompatible_python(request: str, mode: str) -> None:
    directory, env, installer = fixture(f"python-{request}-{mode}")
    wheel(directory / "wheels", "zenml", "0.98.1")
    wheel(directory / "wheels", "zenml", "0.1.0", ">=3.8")
    project(directory, ">=3.9")
    before = (directory / "pyproject.toml").read_bytes()
    args = []
    if mode == "pin":
        (directory / ".python-version").write_text(request + "\n")
    elif mode == "environment":
        env["UV_PYTHON"] = request
    elif mode == "existing-venv":
        subprocess.run([uv, "venv", "--python", request, str(directory / ".venv")], env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        args = [f"--python={request}"]
    output = run(directory, env, installer, "--project", "--no-modify-path", "--extras=", *args, success=False)
    assert "Python" in output and ("3.10" in output or "supported" in output), output
    assert (directory / "pyproject.toml").read_bytes() == before
    assert not (directory / "uv.lock").exists()


def historical_floor() -> None:
    directory, env, installer = fixture("floor")
    wheel(directory / "wheels", "zenml", "0.1.0")
    wheel(directory / "wheels", "zenml", "0.98.1", dependencies=("dependency-fixture>=2",))
    wheel(directory / "wheels", "dependency-fixture", "1.0.0")
    project(directory, dependencies=("dependency-fixture<2",))
    run(directory, env, installer, "--project", "--no-modify-path", "--extras=", success=False)
    run(directory, env, installer, "--project", "--no-modify-path", "--extras=", "--version=0.1.0")
    assert read_version(directory / ".venv/bin/zenml") == "0.1.0"


def broken_cli(scope: str) -> None:
    directory, env, installer = fixture(f"broken-{scope}")
    wheel(directory / "wheels", "zenml", "0.98.1", broken=True)
    if scope == "project":
        project(directory)
    output = run(directory, env, installer, f"--{scope}", "--no-modify-path", "--extras=", f"--python={sys.executable}", success=False)
    assert "ZenML is installed" not in output, output


def project_upgrade() -> None:
    directory, env, installer = fixture("upgrade")
    project(directory)
    wheel(directory / "wheels", "zenml", "0.98.1")
    run(directory, env, installer, "--project", "--no-modify-path", "--extras=")
    assert read_version(directory / ".venv/bin/zenml") == "0.98.1", "installer changed exact user pin"
    wheel(directory / "wheels", "zenml", "0.98.2")
    run(directory, env, installer, "--project", "--no-modify-path", "--extras=")
    assert read_version(directory / ".venv/bin/zenml") == "0.98.2"
    subprocess.run([uv, "add", "--quiet", "zenml==0.98.1"], cwd=directory, env=env, check=True)
    run(directory, env, installer, "--project", "--no-modify-path", "--extras=")
    assert read_version(directory / ".venv/bin/zenml") == "0.98.1", "installer changed exact user pin"
    assert "zenml==0.98.1" in (directory / "pyproject.toml").read_text()


def global_upgrade() -> None:
    directory, env, installer = fixture("global-upgrade")
    wheel(directory / "wheels", "zenml", "0.98.1", dependencies=('server-fixture; extra == "server"',))
    wheel(directory / "wheels", "server-fixture", "1.0.0")
    wheel(directory / "wheels", "addon-fixture", "1.0.0")
    run(directory, env, installer, "--global", "--no-modify-path", "--extras=server", "--with=addon-fixture", f"--python={sys.executable}")
    python = directory / "tools/zenml/bin/python"
    original = subprocess.check_output([str(python), "-c", "import sys; print(sys.base_prefix)"], text=True)
    wheel(directory / "wheels", "zenml", "0.98.2", dependencies=('server-fixture; extra == "server"',))
    run(directory, env, installer, "--global", "--no-modify-path")
    assert read_version(directory / "bin/zenml") == "0.98.2"
    subprocess.run([str(python), "-c", "from importlib.metadata import version; assert version('server-fixture') == '1.0.0'; assert version('addon-fixture') == '1.0.0'"], check=True)
    assert subprocess.check_output([str(python), "-c", "import sys; print(sys.base_prefix)"], text=True) == original


def foreign_project(kind: str) -> None:
    directory, env, installer = fixture(f"foreign-{kind}")
    wheel(directory / "wheels", "zenml", "0.98.1")
    if kind == "poetry":
        project(directory)
        (directory / "poetry.lock").write_text("# untouched Poetry lock\n")
    elif kind == "pdm":
        project(directory)
        (directory / "pdm.lock").write_text("# untouched PDM lock\n")
    elif kind == "tool-only":
        (directory / "pyproject.toml").write_text("[tool.ruff]\nline-length = 88\n")
    else:
        (directory / "uv.lock").write_text("version = 1\n")
    before = {p.name: p.read_bytes() for p in directory.iterdir() if p.suffix in (".toml", ".lock")}
    run(directory, env, installer, "--no-modify-path", f"--python={sys.executable}", success=False)
    assert {p.name: p.read_bytes() for p in directory.iterdir() if p.suffix in (".toml", ".lock")} == before
    assert not (directory / ".venv").exists()
    assert not (directory / "tools/zenml").exists()


def missing_flag(flag: str, next_option: bool) -> None:
    directory, env, installer = fixture(f"flag-{flag[2:]}-{next_option}")
    args = [flag, "--global"] if next_option else [flag]
    output = run(directory, env, installer, *args, success=False)
    assert flag in output and any(word in output.lower() for word in ("requires", "value", "missing", "expected")), output


def shell_setup(destination: str, no_modify: bool, broken: bool = True, profile_failure: bool = False) -> None:
    directory, env, installer = fixture(f"shell-{destination}-{no_modify}-{profile_failure}")
    wheel(directory / "wheels", "zenml", "0.98.1")
    stubs = directory / "stubs"
    stubs.mkdir()
    # Never allow uv's real HOME-based shell writer to reach user profiles.
    wrapper = f'#!/bin/sh\nif [ "$1 $2" = "tool update-shell" ]; then exit 1; fi\nexec "{uv}" "$@"\n'
    if broken:
        (stubs / "uv").write_text("#!/bin/sh\nexit 1\n")
        (stubs / "uv").chmod(0o755)
    else:
        (stubs / "uv").write_text(wrapper)
        (stubs / "uv").chmod(0o755)
    target = directory / "custom-bin"
    if destination != "default":
        env[destination] = str(target)
    else:
        env.pop("XDG_DATA_HOME", None)
        target = Path(env["TEST_HOME"]) / ".local/bin"
    bootstrap = directory / "bootstrap.sh"
    bootstrap.write_text(
        '#!/bin/sh\nprintf "%s\\n%s\\n" "$PATH" "${UV_NO_MODIFY_PATH:-unset}" > "$BOOTSTRAP_OBSERVED"\n'
        f'mkdir -p "{target}"\ncat > "{target}/uv" <<\'WRAPPER\'\n{wrapper}WRAPPER\nchmod +x "{target}/uv"\n'
    )
    (stubs / "curl").write_text(f'#!/bin/sh\ncat "{bootstrap}"\n')
    (stubs / "curl").chmod(0o755)
    env.update(PATH=str(stubs) + os.pathsep + base["PATH"], BOOTSTRAP_OBSERVED=str(directory / "observed"), SHELL="/bin/sh")
    if profile_failure:
        (Path(env["TEST_HOME"]) / ".profile").mkdir()
    args = ["--global", "--extras=", f"--python={sys.executable}"]
    if no_modify:
        args.append("--no-modify-path")
    output = run(directory, env, installer, *args)
    if broken:
        observed = (directory / "observed").read_text().splitlines()
        assert observed[0] == env["PATH"], observed
        assert observed[1] == ("1" if no_modify else "unset"), observed
    if no_modify:
        assert not (Path(env["TEST_HOME"]) / ".profile").exists()
    if profile_failure:
        assert "export PATH=" in output and ("warn" in output.lower() or "could not" in output.lower() or "!" in output), output
    assert "ZenML is installed" in output, output


def bash_login_path(startup):
    directory, env, _ = fixture(f"bash-login-{startup}")
    home = Path(env["TEST_HOME"])
    binaries = home / ".local/bin"
    binaries.mkdir(parents=True)
    binary = binaries / "zenml"
    binary.write_text("#!/bin/sh\necho zenml-fixture\n")
    binary.chmod(0o755)
    fallback = home / ".profile"
    fallback.write_text(f'export PATH="{binaries}:$PATH"\n')
    fallback_before = fallback.read_bytes()
    selected = home / startup
    selected.write_text("RUNNER_PROFILE_LOADED=1\n")
    if startup == ".bash_profile":
        (home / ".bash_login").write_text("echo this-lower-priority-file-must-not-run\n")
    definition = "persist_path() {" + source.read_text().split("persist_path() {", 1)[1].split("\n}", 1)[0] + "\n}\n"
    definition = definition.replace("$HOME", "$TEST_HOME")
    env.update(PATH="/usr/bin:/bin", SHELL="/bin/bash", STARTUP=startup)
    command = definition + '\nwarn() { echo "$*" >&2; }; persist_path "$TEST_HOME/.local/bin"'
    subprocess.run([sys.argv[3], "-eu", "-c", command], env=env, check=True, capture_output=True, text=True)
    probe = subprocess.run([sys.argv[3], "--noprofile", "--norc", "-ec",
                            '. "$TEST_HOME/$STARTUP"; test "$RUNNER_PROFILE_LOADED" = 1; zenml --version'],
                           env=env, capture_output=True, text=True)
    assert probe.returncode == 0 and "zenml-fixture" in probe.stdout, probe.stderr
    first = selected.read_bytes()
    subprocess.run([sys.argv[3], "-eu", "-c", command], env=env, check=True, capture_output=True, text=True)
    assert selected.read_bytes() == first, "Rerun duplicated shell configuration"
    assert fallback.read_bytes() == fallback_before, "Changed the inactive .profile"


def windows_python_paths():
    directory, env, _ = fixture("windows-python-paths")
    project(directory)
    stubs = directory / "stubs"
    stubs.mkdir()
    native = r"C:\fixture\python.exe"
    (stubs / "uv").write_text(f"#!/bin/sh\nprintf '%s\\n' '{native}'\n")
    (stubs / "cygpath").write_text(f"#!/bin/sh\nprintf '%s\\n' '{sys.executable}'\n")
    for stub in stubs.iterdir():
        stub.chmod(0o755)
    env.update(PATH=str(stubs) + os.pathsep + env["PATH"], PROJECT_DIR=str(directory),
               PROJECT_PYTHON_SCRIPT=str(directory / "project-python.py"), UV=str(stubs / "uv"),
               ZENML_SUPPORTED_PYTHON=">=3.10,<3.15", IS_WINDOWS="1")
    definitions = ""
    for name in ("find_requested_python", "prepare_project_python"):
        definitions += name + "() {" + source.read_text().split(name + "() {", 1)[1].split("\n}", 1)[0] + "\n}\n"
    result = subprocess.run([sys.argv[3], "-eu", "-c", definitions +
                             '\nfind_requested_python custom; prepare_project_python'],
                            env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == sys.executable, result.stdout
    assert (directory / "project-python.py").is_file()


def install_report():
    directory, env, _ = fixture("install-report")
    observed = directory / "reported"
    stub = directory / "zenml"
    stub.write_text(f'#!/bin/sh\nprintf "%s\\n" "$*" > "{observed}"\n')
    stub.chmod(0o755)
    definitions = "REPORT_PID=\nC_DIM=\nC_RESET=\n"
    for name in ("analytics_opted_out", "report_install", "wait_for_report"):
        definitions += name + "() {" + source.read_text().split(name + "() {", 1)[1].split("\n}", 1)[0] + "\n}\n"
    for opt_out, expected in (({}, "analytics report-install --scope global"),
                              ({"ZENML_ANALYTICS_OPT_IN": "false"}, None), ({"DO_NOT_TRACK": "1"}, None)):
        observed.unlink(missing_ok=True)
        case_env = {key: value for key, value in env.items() if key not in ("ZENML_ANALYTICS_OPT_IN", "DO_NOT_TRACK")}
        case_env.update(opt_out, ZENML_BIN=str(stub), ZENML_INSTALL_SCOPE="global")
        result = subprocess.run([sys.argv[3], "-eu", "-c", definitions + "\nreport_install; wait_for_report"],
                                env=case_env, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        reported = observed.read_text().strip() if observed.exists() else None
        assert reported == expected, f"{opt_out}: {reported!r}"
        # The notice goes to stderr, so --quiet cannot hide it, and only when an event is sent.
        assert ("anonymous usage data" in result.stderr) == bool(expected), result.stderr
    # A CLI without the command (an older pinned ZenML) must not fail the install.
    stub.write_text("#!/bin/sh\nexit 2\n")
    result = subprocess.run([sys.argv[3], "-eu", "-c", definitions + "\nreport_install; wait_for_report"],
                            env={**case_env, "DO_NOT_TRACK": "0"}, capture_output=True, text=True)
    assert result.returncode == 0 and not result.stdout, result.stderr
    assert [line for line in result.stderr.splitlines() if "ZENML" not in line.upper()] == [], result.stderr


cases = [("capped project chooses intersection", capped_project), ("historical release floor and explicit override", historical_floor),
         ("project version transition and exact user pin", project_upgrade), ("global upgrade preserves extras, add-ons and Python", global_upgrade)]
cases.append(("Git Bash normalizes uv Python paths", windows_python_paths))
cases.append(("install report honors analytics opt-out", install_report))
for startup in (".bash_profile", ".bash_login"):
    cases.append((f"Bash login PATH with {startup}", lambda s=startup: bash_login_path(s)))
for request in ("3.9", "3.15"):
    for mode in ("pin", "environment", "explicit", "existing-venv"):
        cases.append((f"reject Python {request} {mode}", lambda r=request, m=mode: incompatible_python(r, m)))
for scope in ("project", "global"):
    cases.append((f"broken {scope} CLI fails", lambda s=scope: broken_cli(s)))
for kind in ("poetry", "pdm", "tool-only", "orphan-lock"):
    cases.append((f"preserve foreign {kind} project", lambda k=kind: foreign_project(k)))
for destination in ("default", "UV_INSTALL_DIR", "XDG_BIN_HOME"):
    for flag in (False, True):
        cases.append((f"bootstrap {destination} no-modify={flag}", lambda d=destination, f=flag: shell_setup(d, f)))
for flag in ("--version", "--extras", "--server", "--with", "--python"):
    for next_option in (False, True):
        cases.append((f"missing {flag} next-option={next_option}", lambda f=flag, n=next_option: missing_flag(f, n)))
cases.append(("unwritable profile warns after install", lambda: shell_setup("default", False, broken=False, profile_failure=True)))
try:
    for label, test in cases:
        if selection != "all" and selection not in label:
            continue
        try:
            test()
        except Exception as error:
            failures.append(label)
            print(f"FAIL: {label}: {error}", flush=True)
        else:
            passed += 1
            print(f"PASS: {label}", flush=True)
    assert passed or failures, f"No regression matches {selection!r}"
    print(f"{passed} passed; {len(failures)} failed", flush=True)
    if failures:
        print(f"Failure artifacts: {root}", flush=True)
        raise SystemExit(1)
finally:
    if not failures:
        shutil.rmtree(root)
PY
