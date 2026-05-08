# Investigation: Dependency audit upgrade risk assessment

## Summary
The audit failures are fixable, but they are four different upgrade problems rather than one generic dependency bump. `orjson` looks low risk; `PyJWT` is feasible with a small decode API modernization; `FastAPI`/`Starlette` is the highest production-risk change because ZenML serves static files and archive downloads through Starlette response paths; `pytest` is the highest diagnostic-risk change because pytest/plugin failures can obscure whether runtime upgrades actually broke ZenML.

## Symptoms
- The new Python Dependency Audit workflow on PR #4805 fails because `pip-audit` reports known vulnerabilities in the installed `.[server,dev,local]` dependency set.
- The goal is to assess whether upgrading the flagged packages is safe before making dependency changes in stacked PRs.

## Background / Prior Research

### GitHub Actions audit failure
- Workflow/job: `Python Dependency Audit` / `Audit zenml server/dev/local dependencies`, job `75004268954`, run `25515905606` on PR #4805.
- Branch: `feature/dependency-audit-ci`; reported merge-ref commit: `8e8761d9efd7823d01aacd5802d8b20271d44b08`.
- Command: `uvx pip-audit --path "$SITE_PACKAGES" --strict --progress-spinner off` against an isolated Python 3.11.15 audit venv.
- Result: failed with 5 known vulnerabilities in 4 packages:

| Package | Installed | Advisory | Fix version |
|---|---:|---|---:|
| `orjson` | `3.10.18` | `CVE-2025-67221` | `3.11.6` |
| `pyjwt` | `2.7.0` | `CVE-2026-32597` | `2.12.0` |
| `pytest` | `7.4.4` | `CVE-2025-71176` | `9.0.3` |
| `starlette` | `0.45.3` | `CVE-2025-54121` | `0.47.2` |
| `starlette` | `0.45.3` | `CVE-2025-62727` | `0.49.1` |

A later rerun (`25556055083`) reportedly failed on the same dependency-audit step, so the PR branch still has unresolved findings.

### External release-note / advisory research

#### `orjson` 3.10.18 → 3.11.6
- Source: https://github.com/ijl/orjson/releases
- Risk assessed as low by external probe.
- Key release-note points:
  - 3.11.x does not appear to change the public `orjson.dumps` / `orjson.loads` API.
  - 3.11.6 drops Python 3.9; ZenML already requires Python >=3.10, so this is acceptable.
  - Build-from-source requirements increase (Rust/C compiler), but normal CI/users should receive wheels.
- Likely constraint change: `orjson~=3.10.0` to a range allowing `3.11.6`, e.g. `orjson~=3.11.0` or `orjson>=3.11.6,<3.12.0`.

#### `PyJWT` 2.7.0 → 2.12.0
- Sources:
  - https://pyjwt.readthedocs.io/en/stable/changelog.html
  - https://github.com/advisories/GHSA-752w-5fwx-jx9f
  - https://github.com/advisories/GHSA-75c5-xw7c-p5pm
- Risk assessed as medium by external probe.
- Security drivers:
  - `CVE-2026-32597` / `GHSA-752w-5fwx-jx9f`: `crit` header validation; fixed in 2.12.0.
  - `CVE-2024-53861` / `GHSA-75c5-xw7c-p5pm`: issuer partial-match issue; fixed in 2.10.1.
- Compatibility points:
  - Python 3.7/3.8 drops are irrelevant for ZenML >=3.10.
  - PyJWT 2.10 removes `algorithm=None` syntax in favor of `algorithm="none"`; ZenML likely uses configured algorithm strings.
  - PyJWT 2.11 introduces minimum-key-length warnings; short local `jwt_secret_key` values may produce warnings.
  - External probe flagged ZenML `src/zenml/zen_server/jwt.py` as likely using deprecated `verify=` in `jwt.decode`; preferred replacement is `options={"verify_signature": False}` when verification is disabled.

#### `Starlette` 0.45.3 → 0.49.1
- Sources:
  - https://www.starlette.io/release-notes/
  - https://github.com/advisories/GHSA-7f5h-v6xp-fcq8
- Risk assessed as high urgency because ZenML server appears to use `FileResponse` and `StaticFiles` paths affected by the advisories.
- Security drivers:
  - `CVE-2025-54121`: UploadFile blocks event loop during large rollover; fixed in 0.47.2.
  - `CVE-2025-62727` / `GHSA-7f5h-v6xp-fcq8`: crafted HTTP Range header quadratic-time DoS in `FileResponse`; fixed in 0.49.1.
- Compatibility points:
  - `MultiPartParser.max_file_size` renamed to `spool_max_size`; likely no impact if ZenML does not instantiate `MultiPartParser` directly.
  - `BaseHTTPMiddleware` background-task exceptions may now surface instead of being suppressed; worth targeted server tests.
  - Starlette is transitive through FastAPI. Clearing this likely requires adjusting the FastAPI bound/resolution so Starlette resolves to >=0.49.1.

#### `pytest` 7.4.4 → 9.0.3
- Sources:
  - https://docs.pytest.org/en/stable/changelog.html
  - https://docs.pytest.org/en/stable/announce/release-8.0.0.html
  - https://docs.pytest.org/en/stable/announce/release-8.4.0.html
  - https://docs.pytest.org/en/stable/announce/release-9.0.0.html
  - https://nvd.nist.gov/vuln/detail/CVE-2025-71176
- Risk assessed as high for test-suite migration, lower for runtime because pytest is a dev dependency.
- Security driver: `CVE-2025-71176`, fixed in 9.0.3; predictable `/tmp/pytest-of-{user}` directory naming on Unix.
- Compatibility concerns across 8.x/9.x:
  - 8.0 turns `PytestRemovedIn8Warning` cases into errors.
  - 8.4 turns tests returning non-`None` into failures and async tests without plugins into errors.
  - 9.0 turns `PytestRemovedIn9Warning` cases into errors and drops Python 3.9, which is acceptable for ZenML >=3.10.
  - Plugin compatibility needs checking for `pytest-randomly`, `pytest-mock`, `pytest-clarity`, `pytest-instafail`, `pytest-rerunfailures`, and `pytest-split`.
## Investigator Findings

### 2026-05-08 stacked-branch follow-up

#### Quick conclusion

The four audit findings should not be fixed in one opaque dependency PR. The safe shape is a small stack of PRs where each layer has a narrow failure mode:

1. **`orjson` only**: low-risk server serialization dependency bump.
2. **`PyJWT` only**: dependency bump plus the one decode modernization, then focused JWT/download-token tests.
3. **FastAPI/Starlette together**: framework bump chosen specifically to permit Starlette `>=0.49.1`, then focused server/static/download/middleware tests.
4. **pytest/tooling last**: separate test-infra PR, because failures here can come from pytest core, plugins, or test patterns rather than ZenML runtime code.

That ordering keeps the story clean: if a JWT test fails, it is not mixed with pytest plugin breakage; if a server route fails, it is not hidden under test-runner migration noise.

#### Dependency bounds and direct usage evidence

Current relevant bounds are in `pyproject.toml`:

- `fastapi>=0.100,<=0.115.8` at `pyproject.toml:82`.
- `pyjwt[crypto]==2.7.*` at `pyproject.toml:85`.
- `orjson~=3.10.0` at `pyproject.toml:87`.
- `pytest>=7.4.0,<8.0.0` at `pyproject.toml:143`.
- pytest plugin bounds at `pyproject.toml:151-156`: `pytest-randomly`, `pytest-mock`, `pytest-clarity`, `pytest-instafail`, `pytest-rerunfailures`, and `pytest-split`.
- pytest config is minimal: `filterwarnings = ["ignore::DeprecationWarning"]`, `testpaths = "tests"`, and `xfail_strict = true` at `pyproject.toml:188-193`.

I also ran a read-only resolver simulation using a generated requirements file under `/private/tmp` rather than editing `pyproject.toml`. A candidate set with `fastapi>=0.120.1,<0.121.0`, `starlette>=0.49.1,<0.50.0`, `orjson>=3.11.6,<3.12.0`, `PyJWT[crypto]>=2.12.0,<2.13.0`, `pytest>=9.0.3,<10.0.0`, `pytest-rerunfailures>=16.1,<17.0.0`, and `pytest-split>=0.11.0,<0.12.0` resolved successfully on Python 3.11. The resolver selected `fastapi==0.120.4`, `starlette==0.49.3`, `orjson==3.11.8`, `pyjwt==2.12.1`, `pytest==9.0.3`, `pytest-rerunfailures==16.1`, and `pytest-split==0.11.0`.

Important caveat: a naive `uv pip install --dry-run -e '.[server,dev,local]' ... orjson>=3.11.6 ...` fails before any useful framework answer because the unmodified project metadata still says `zenml[server]` depends on `orjson>=3.10.0,<3.11.dev0`. That confirms the resolver conflict is exactly the existing bound, not an external incompatibility.

#### 1. `orjson`: low code risk, one runtime smoke test is enough

Evidence:

- ZenML declares `orjson` only in the server extra at `pyproject.toml:87`.
- A repo-wide search found no direct `import orjson` or direct `orjson.dumps` / `orjson.loads` calls in `src` or `tests`; the only project hit is the dependency line.
- ZenML uses FastAPI's `ORJSONResponse`, not direct `orjson` APIs: imported at `src/zenml/zen_server/zen_server_api.py:32`, configured as the FastAPI default response class at `src/zenml/zen_server/zen_server_api.py:125-130`, and returned by the request-validation handler at `src/zenml/zen_server/zen_server_api.py:137-150`.
- A temporary import/runtime probe with `fastapi==0.120.4`, `starlette>=0.49.1,<0.50`, and `orjson>=3.11.6,<3.12` rendered `ORJSONResponse({"ok": True})` as `b'{"ok":true}'`.

Assessment: **low risk**. ZenML is not using `orjson`'s lower-level API surface; it is relying on FastAPI's response class. The main validation needed is that the server still imports and returns JSON responses.

Recommended validation:

```bash
uv run pytest tests/unit/zen_server/test_jwt.py
uv run pytest tests/integration/functional/zen_server/test_zen_server.py
```

The JWT test is not about `orjson` directly, but it imports server configuration and catches obvious server-import fallout cheaply. If there is a dedicated API response serialization test elsewhere, add it to this layer too.

#### 2. `PyJWT`: feasible, but `verify=` is now a real breakage point

Evidence:

- `JWTToken.decode_token()` calls `jwt.decode(..., verify=verify, ...)` at `src/zenml/zen_server/jwt.py:87-95`.
- `JWTToken.encode()` uses a normal configured algorithm string at `src/zenml/zen_server/jwt.py:222-226`, so the removed `algorithm=None` pattern is not a concern here.
- Download-token generation and verification are separate from `JWTToken`: `generate_download_token()` encodes a payload with `download_type` and `resource_id` at `src/zenml/zen_server/auth.py:1134-1147`; `verify_download_token()` decodes and validates those claims at `src/zenml/zen_server/auth.py:1170-1191`.
- The two download-token consumers are artifact data download and snapshot code download: token generation/verification paths at `src/zenml/zen_server/routers/artifact_version_endpoints.py:364-367` and `src/zenml/zen_server/routers/artifact_version_endpoints.py:387-400`; snapshot code paths at `src/zenml/zen_server/routers/pipeline_snapshot_endpoints.py:294-297` and `src/zenml/zen_server/routers/pipeline_snapshot_endpoints.py:318-348`.
- Existing JWT tests already use the modern no-signature-verification style in helper code: `options={"verify_signature": False, "verify_exp": False, "verify_aud": False, "verify_iss": False}` at `tests/unit/zen_server/test_jwt.py:95-104` and `tests/unit/zen_server/test_jwt.py:131-140`.
- A temporary PyJWT 2.12.1 probe showed that `jwt.decode(token, wrong_key, algorithms=[...], verify=False)` still verifies the signature and raises `InvalidSignatureError`; the modern `options={"verify_signature": False}` form succeeds. In plain terms: ZenML currently passes the old “please do not check the signature” flag, but PyJWT 2.12 behaves as if nobody heard that instruction.
- The default ZenML JWT secret is generated with `token_hex(32)` at `src/zenml/config/server_config.py:71-79` and assigned via `Field(default_factory=generate_jwt_secret_key)` at `src/zenml/config/server_config.py:271`, so default local secrets should satisfy PyJWT's newer HMAC key-length warning. User-supplied short `ZENML_SERVER_JWT_SECRET_KEY` values could still emit warnings.

Assessment: **medium risk, feasible**. The likely source change is small: replace the deprecated/ignored `verify=` argument in `JWTToken.decode_token()` with an `options` mapping when verification is disabled. The important behavioral check is not just “login token decodes”; it is also “unsigned/wrong-signature decode is allowed only where ZenML intentionally disables verification,” and “download tokens still reject wrong type/resource/extra claims.”

Exact areas needing tests:

- `src/zenml/zen_server/jwt.py:87-95`: modernization of `verify=False` behavior.
- `src/zenml/zen_server/auth.py:1170-1191`: download-token decode/claim validation under PyJWT 2.12.x.
- `src/zenml/zen_server/routers/artifact_version_endpoints.py:364-400`: artifact archive download token path.
- `src/zenml/zen_server/routers/pipeline_snapshot_endpoints.py:294-348`: snapshot code download token path.

Recommended validation:

```bash
uv run pytest tests/unit/zen_server/test_jwt.py
uv run pytest tests/unit/zen_server -k 'download or token or auth'
uv run pytest tests/integration/functional/zen_server/test_zen_server.py
```

If no focused download-token tests exist yet, add small unit coverage around `generate_download_token()` / `verify_download_token()` before bumping or in the same PyJWT PR.

#### 3. Starlette: cannot be remediated safely by a direct Starlette constraint alone

Evidence:

- The current FastAPI cap is `fastapi>=0.100,<=0.115.8` at `pyproject.toml:82`.
- PyPI metadata checked during this investigation shows FastAPI `0.115.8` requires `starlette>=0.40.0,<0.46.0`, so it cannot resolve Starlette `>=0.49.1`.
- FastAPI metadata then opens the Starlette upper bound gradually: `0.116.1` allows `<0.48.0`, `0.116.2` through `0.120.0` allow `<0.49.0`, and `0.120.1` through `0.121.2` allow `<0.50.0`. Therefore the smallest FastAPI line I found that can carry Starlette `>=0.49.1` is FastAPI `0.120.1+`.
- Direct Starlette usage exists in server runtime code:
  - `StaticFiles` imported at `src/zenml/zen_server/zen_server_api.py:33` and mounted for dashboard assets at `src/zenml/zen_server/zen_server_api.py:200-207`.
  - `FileResponse` imported from Starlette at `src/zenml/zen_server/zen_server_api.py:35-38` and used for dashboard root static files at `src/zenml/zen_server/zen_server_api.py:369-372`.
  - `FileResponse` imported from FastAPI response re-export in artifact and snapshot routers at `src/zenml/zen_server/routers/artifact_version_endpoints.py:20-23` and `src/zenml/zen_server/routers/pipeline_snapshot_endpoints.py:20-23`; archive responses are returned at `src/zenml/zen_server/routers/artifact_version_endpoints.py:396-400` and `src/zenml/zen_server/routers/pipeline_snapshot_endpoints.py:343-348`.
  - `BaseHTTPMiddleware` imported at `src/zenml/zen_server/middleware.py:26-29`; custom middleware classes inherit it at `src/zenml/zen_server/middleware.py:74-113`; multiple `BaseHTTPMiddleware` dispatch middlewares are registered at `src/zenml/zen_server/middleware.py:408-430`.
- Eliminated upload-parser concern: no direct `UploadFile` or `MultiPartParser` usage was found in `src/zenml/zen_server`; ZenML's upload control is custom middleware checking `multipart/form-data` by request path at `src/zenml/zen_server/middleware.py:138-149`, with an empty allowlist at `src/zenml/zen_server/middleware.py:161`.

Assessment: **medium/high runtime risk, but manageable if isolated**. The vulnerable APIs are on ZenML's real serving path (`FileResponse` and `StaticFiles`), so this should be fixed promptly. The safer remediation is **not** “add `starlette>=0.49.1` while keeping FastAPI unchanged,” because that cannot resolve. The safer shape is a conservative FastAPI bump to the smallest compatible range plus an explicit Starlette floor/ceiling, e.g. FastAPI `>=0.120.1,<0.121.0` with Starlette `>=0.49.1,<0.50.0`. That avoids jumping all the way to the latest FastAPI/Starlette line while still clearing the audit finding.

Recommended validation:

```bash
uv run pytest tests/integration/functional/zen_server/test_zen_server.py
uv run pytest tests/unit/zen_server
uv run pytest tests/integration/functional/zen_server -k 'server or auth or download or artifact or snapshot'
```

Manual/API smoke worth doing if the PR is close to merge: start a local ZenML server, fetch a dashboard asset under `/assets`, fetch a root static file that uses the catch-all `FileResponse`, request an artifact/snapshot download token, then download with the token. Also send a `Range` header against one `FileResponse` endpoint to make sure the response still behaves sanely after the Starlette change.

#### 4. `pytest`: highest migration risk and should be a separate tooling PR

Evidence:

- Current pytest is capped below 8 at `pyproject.toml:143`, so going to `pytest==9.0.3` crosses two major pytest migrations.
- Current plugin bounds are at `pyproject.toml:151-156`.
- PyPI metadata checked during this investigation shows current `pytest-split==0.10.0` requires `pytest<9,>=5`; the `pytest-split` bound must move to `>=0.11.0,<0.12.0` for pytest 9 because `pytest-split==0.11.0` requires `pytest<10,>=5`.
- `pytest-rerunfailures==16.1` explicitly supports `pytest>=7.4` except `8.2.2`; the current bound `<14.0.0` does not force that newer tested line. The resolver candidate used `pytest-rerunfailures>=16.1,<17.0.0` successfully.
- Existing test runner commands depend on these plugins: `scripts/test-coverage-xml.sh:44` builds `--reruns` args; `scripts/test-coverage-xml.sh:56-66` uses `--reruns`, `--instafail`, `--splits`, `--group`, `--splitting-algorithm`, `--store-durations`, and `--durations-path`.
- Custom ZenML pytest options are registered in `tests/conftest.py:55-110` (`--environment`, `--deployment`, `--requirements`, `--no-teardown`, `--no-cleanup`, `--no-provision`, `--cleanup-docker`). Those should be validated under pytest 9 because option parsing/plugin startup failures happen before test bodies run.
- Eliminated concerns from static checks:
  - No collected test function directly returns non-`None` from its top-level body, so the pytest 8.4 “test returned non-None” hard failure does not currently look like a bulk migration issue.
  - No `async def test_...` functions were found, so the pytest 8.4 async-test-without-plugin failure is not currently a bulk issue.
  - No `pytest.importorskip` usage was found.
  - No `PytestRemoved...` warning filters or direct references were found.
- One concrete pytest API breakage was found: `pytest.warns(None)` at `tests/unit/utils/test_exception_utils.py:42`. A temporary pytest 9.0.3 probe raises `TypeError: exceptions must be derived from Warning, not <class 'NoneType'>` for `pytest.warns(None)`, so this test needs modernization before/with the pytest bump.

Assessment: **highest migration risk, but mostly test-infra risk rather than runtime risk**. The branch should not mix this with FastAPI/Starlette or PyJWT changes. Think of pytest 9 as replacing the measuring equipment while the other PRs change the machine under test; do not do both at once or failures become hard to interpret.

Recommended validation strategy:

1. First update pytest/plugin bounds only enough to resolve: `pytest>=9.0.3,<10`, `pytest-split>=0.11.0,<0.12.0`, and likely `pytest-rerunfailures>=16.1,<17.0.0`.
2. Fix `tests/unit/utils/test_exception_utils.py:42` (`pytest.warns(None)`) using the modern `warnings.catch_warnings(record=True)` pattern or pytest's current recommended no-warning assertion style.
3. Validate pytest startup and custom options before running large suites:

```bash
uv run pytest --version
uv run pytest --collect-only tests/unit/zen_server/test_jwt.py
uv run pytest --collect-only tests/unit
uv run pytest tests/unit/utils/test_exception_utils.py
uv run pytest tests/unit/zen_server/test_jwt.py
```

4. Then validate the plugin-heavy path:

```bash
PYTEST_RERUNS=0 bash scripts/test-coverage-xml.sh unit default 1 1
```

Use CI for broad integration coverage after the fast local collection/unit checks pass.

#### Recommended stacked PR order

1. **PR A: `orjson` audit remediation.** Only change the `orjson` bound. Run server import/API serialization smoke tests.
2. **PR B: PyJWT 2.12.x.** Change the PyJWT bound and modernize `JWTToken.decode_token()` around disabled verification. Add/validate download-token tests.
3. **PR C: FastAPI/Starlette remediation.** Raise FastAPI just enough to permit Starlette `>=0.49.1`, add an explicit Starlette floor and conservative ceiling, and validate dashboard/static/download/middleware routes.
4. **PR D: pytest 9/tooling.** Update pytest and plugin bounds, fix `pytest.warns(None)`, and validate collection/custom options/plugin command paths.

#### Temporary files/cache cleanup note

This investigation used only temporary resolver/runtime probes under `/private/tmp` and did not edit source or dependency files. The generated probe paths were removed after use:

```bash
rm -rf /private/tmp/zenml-dep-audit-venv /private/tmp/zenml-dep-audit-uv-cache /private/tmp/zenml-dep-audit-reqs.txt
```

## Investigation Log

### Initial setup - report created
**Hypothesis:** The audit failures can likely be fixed with targeted dependency bound updates, but each flagged package needs release-note and code-usage review before changing constraints.
**Findings:** Investigation started on a branch stacked on `feature/dependency-audit-ci`.
**Evidence:** PR #4805 dependency audit workflow; GitHub Actions run/job supplied by user.
**Conclusion:** Needs more investigation.

## Root Cause
The dependency audit fails because ZenML's current dependency bounds prevent the resolver from selecting versions that contain the relevant security fixes:

- `orjson~=3.10.0` keeps the server extra below the audited fix version `3.11.6`.
- `pyjwt[crypto]==2.7.*` keeps ZenML below PyJWT's newer issuer and `crit` header validation fixes; upgrading exposes a real compatibility issue in `JWTToken.decode_token()`, which still passes the old `verify=` argument to `jwt.decode`.
- `fastapi>=0.100,<=0.115.8` indirectly keeps Starlette below the audit-required `0.49.1`; FastAPI `0.115.8` cannot resolve with Starlette `>=0.49.1`, so the framework bound must move.
- `pytest>=7.4.0,<8.0.0` keeps the dev environment below the pytest `9.0.3` CVE fix, and crossing to pytest 9 also requires plugin/test-suite cleanup.

The practical consequence is that the audit branch is doing its job: it has exposed security fixes that require deliberate, layered remediation rather than a single blind lock refresh.

## Recommendations
1. **Start with a pytest/tooling compatibility PR, or run pytest-9 validation from the start.** Oracle's procedural correction is important: if the test harness remains on pytest 7 while runtime dependency PRs land, the final pytest 9 PR may reveal failures whose true source is ambiguous. Preferred first PR: bump pytest/plugins enough to support pytest `9.0.3`, fix `tests/unit/utils/test_exception_utils.py:42` (`pytest.warns(None)`), and validate collection/custom plugin options.

2. **Then make a small `orjson` PR.** This is the lowest-risk runtime change because ZenML does not directly import `orjson`; it uses FastAPI's `ORJSONResponse`. Allow `orjson>=3.11.6,<3.12` or equivalent and run representative server/API serialization smoke tests.

3. **Make a focused PyJWT PR.** Bump PyJWT to the fixed 2.12 line and modernize `src/zenml/zen_server/jwt.py:87-95` from `verify=verify` to the current `options={...}` form when verification is disabled. Validate normal auth tokens plus the separate download-token flow in `src/zenml/zen_server/auth.py:1134-1191` and its artifact/snapshot consumers.

4. **Make a separate FastAPI/Starlette PR.** Do not force Starlette under the old FastAPI cap. Raise FastAPI to the smallest compatible range found by resolver testing, e.g. FastAPI `>=0.120.1,<0.121`, and add an explicit Starlette safety range such as `starlette>=0.49.1,<0.50`. Validate server startup/shutdown, `/health`, `/ready`, dashboard/static assets, `FileResponse` archive downloads, background cleanup, CORS, and multipart/request-size middleware behavior.

5. **Review the full resolved dependency diff for each PR.** Especially for the FastAPI/Starlette and PyJWT PRs, inspect transitive movement in packages such as `anyio`, `cryptography`, `typing-extensions`, `python-multipart`, and any test-client-related dependencies before assuming only the named audit packages changed.

Suggested validation commands from the investigation:

```bash
# pytest/tooling PR
uv run pytest --version
uv run pytest --collect-only tests/unit/zen_server/test_jwt.py
uv run pytest --collect-only tests/unit
uv run pytest tests/unit/utils/test_exception_utils.py
uv run pytest tests/unit/zen_server/test_jwt.py

# PyJWT PR
uv run pytest tests/unit/zen_server/test_jwt.py -q
uv run pytest tests/unit/zen_server -k 'download or token or auth' -q
uv run pytest tests/integration/functional/zen_server/test_zen_server.py -q

# FastAPI/Starlette PR
uv run pytest tests/integration/functional/zen_server/test_zen_server.py -q
uv run pytest tests/unit/zen_server -q
uv run pytest tests/integration/functional/zen_server -k 'server or auth or download or artifact or snapshot' -q
```

## Preventive Measures
- Keep the dependency audit workflow as a regular scheduled and PR-triggered signal, but treat first adoption as a baseline-building exercise.
- For security-driven dependency work, split PRs by failure mode: test tooling, auth/security libraries, web framework/runtime, and serialization should not all move in one PR.
- When Starlette/FastAPI moves, add or maintain focused regression tests for static files, archive downloads, background cleanup, middleware short-circuiting, and multipart rejection.
- When PyJWT moves, keep focused tests for both normal bearer-token auth and ZenML's separate short-lived download-token flow.
- Record the resolved dependency diff in each stacked PR description so reviewers can see unexpected transitive upgrades early.
