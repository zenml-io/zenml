#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

import os
from contextlib import ExitStack as does_not_raise

import pytest
from pydantic import BaseModel

from zenml.utils.env_utils import (
    ConfigBase,
    reconstruct_environment_variables,
    split_environment_variables,
    substitute_env_variable_placeholders,
)


def test_split_reconstruct_large_env_vars():
    """Test that splitting and reconstructing large environment variables works."""
    env = {
        "ARIA_TEST_ENV_VAR": "aria",
        "AXL_TEST_ENV_VAR": "axl is gray and puffy",
        "BLUPUS_TEST_ENV_VAR": "blupus",
    }

    split_environment_variables(env=env, size_limit=4)

    assert env == {
        "ARIA_TEST_ENV_VAR": "aria",
        "AXL_TEST_ENV_VAR_CHUNK_0": "axl ",
        "AXL_TEST_ENV_VAR_CHUNK_1": "is g",
        "AXL_TEST_ENV_VAR_CHUNK_2": "ray ",
        "AXL_TEST_ENV_VAR_CHUNK_3": "and ",
        "AXL_TEST_ENV_VAR_CHUNK_4": "puff",
        "AXL_TEST_ENV_VAR_CHUNK_5": "y",
        "BLUPUS_TEST_ENV_VAR_CHUNK_0": "blup",
        "BLUPUS_TEST_ENV_VAR_CHUNK_1": "us",
    }

    reconstruct_environment_variables(env=env)

    assert env == {
        "ARIA_TEST_ENV_VAR": "aria",
        "AXL_TEST_ENV_VAR": "axl is gray and puffy",
        "BLUPUS_TEST_ENV_VAR": "blupus",
    }


def test_split_too_large_env_var_fails():
    """Test that splitting and reconstructing too large an environment variable fails."""
    env = {
        "ARIA_TEST_ENV_VAR": "aria",
        "AXL_TEST_ENV_VAR": "axl is gray and puffy and wonderful",
    }

    with does_not_raise():
        split_environment_variables(env=env, size_limit=4)

    env = {
        "ARIA_TEST_ENV_VAR": "aria",
        "AXL_TEST_ENV_VAR": "axl is gray and puffy and wonderful and otherworldly",
    }

    with pytest.raises(RuntimeError):
        split_environment_variables(env=env, size_limit=4)


def test_env_var_substitution(mocker):
    """Test environment var substitution."""
    mocker.patch.dict(os.environ, {"A": "1"})

    class M(BaseModel):
        string_attribute: str

    assert (
        substitute_env_variable_placeholders("prefix_${A}_suffix")
        == "prefix_1_suffix"
    )

    # Non existent -> Raise when configured
    with pytest.raises(KeyError):
        substitute_env_variable_placeholders(
            "prefix_${B}_suffix", raise_when_missing=True
        )

    # Non existent -> empty string
    assert (
        substitute_env_variable_placeholders(
            "prefix_${B}_suffix", raise_when_missing=False
        )
        == "prefix__suffix"
    )

    # Wrong patterns
    assert (
        substitute_env_variable_placeholders("prefix_{A}_suffix")
        == "prefix_{A}_suffix"
    )
    assert (
        substitute_env_variable_placeholders("prefix_{{A}}_suffix")
        == "prefix_{{A}}_suffix"
    )

    # Complex objects
    key = "prefix_${A}_suffix"
    val = "prefix_1_suffix"
    combined = [
        2,
        0.2,
        None,
        key,
        {3: key, key: M(string_attribute=key)},
        set([key, 4]),
    ]
    assert substitute_env_variable_placeholders(combined) == [
        2,
        0.2,
        None,
        val,
        {3: val, val: M(string_attribute=val)},
        set([val, 4]),
    ]


class DBConfig(ConfigBase):
    conn_url: str

    @staticmethod
    def prefixes() -> list[str]:
        return ["ZENML_DB_"]


class CacheConfig(ConfigBase):
    redis_url: str

    @staticmethod
    def prefixes() -> list[str]:
        return ["ZENML_REDIS_"]


class CombinedConfig(DBConfig, CacheConfig):
    """Multiple inheritance: merges env vars from DBConfig + CacheConfig."""

    @staticmethod
    def prefixes() -> list[str]:
        return DBConfig.prefixes() + CacheConfig.prefixes()


class TwoPrefixConfig(ConfigBase):
    """Single class with two prefixes, to test longest-prefix-first behavior."""

    conn_url: str

    @staticmethod
    def prefixes() -> list[str]:
        # Intentionally includes an overlapping shorter prefix.
        return ["ZENML_", "ZENML_DB_"]


class NonConflictingCombinedConfig(ConfigBase):
    """Demonstrates how to avoid conflicts via more specific variable names."""

    db_conn_url: str
    redis_conn_url: str

    @staticmethod
    def prefixes() -> list[str]:
        return ["ZENML_"]


def _clear_related_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove any env vars used by these tests to avoid cross-test leakage."""
    for key in list(os.environ.keys()):
        if key.startswith("ZENML_"):
            monkeypatch.delenv(key, raising=False)


def test_env_resolution_expected_behaviors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Covers multi-class inheritance merge + longest-prefix precedence + instantiation."""
    _clear_related_env(monkeypatch)

    # Multi-class inheritance: two different prefixes, no conflicts.
    monkeypatch.setenv("ZENML_DB_CONN_URL", "postgresql://db")
    monkeypatch.setenv("ZENML_REDIS_REDIS_URL", "redis://cache")

    params = CombinedConfig.get_env_vars()
    assert params == {
        "conn_url": "postgresql://db",
        "redis_url": "redis://cache",
    }

    cfg = CombinedConfig.load_from_env()
    assert cfg.conn_url == "postgresql://db"
    assert cfg.redis_url == "redis://cache"

    # Longest-prefix-first: ZENML_DB_ should win and be consumed, not also matched by ZENML_.
    _clear_related_env(monkeypatch)
    monkeypatch.setenv("ZENML_DB_CONN_URL", "postgresql://db")
    params2 = TwoPrefixConfig.get_env_vars()
    assert params2 == {"conn_url": "postgresql://db"}

    cfg2 = TwoPrefixConfig.load_from_env()
    assert cfg2.conn_url == "postgresql://db"

    # Avoid conflicts with more specific variable names under a shared prefix.
    _clear_related_env(monkeypatch)
    monkeypatch.setenv(
        "ZENML_DB_CONN_URL", "postgresql://db"
    )  # -> db_conn_url
    monkeypatch.setenv(
        "ZENML_REDIS_CONN_URL", "redis://cache"
    )  # -> redis_conn_url
    params3 = NonConflictingCombinedConfig.get_env_vars()
    assert params3 == {
        "db_conn_url": "postgresql://db",
        "redis_conn_url": "redis://cache",
    }


def test_env_resolution_unexpected_behaviors_raise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Covers conflict recognition and invalid instantiation failures."""
    _clear_related_env(monkeypatch)

    # Conflict pattern from docstring: two different prefixes, same suffix -> same variable name after stripping.
    # ZENML_DB_CONN_URL -> conn_url
    # ZENML_REDIS_CONN_URL -> conn_url
    monkeypatch.setenv("ZENML_DB_CONN_URL", "postgresql://db")
    monkeypatch.setenv("ZENML_REDIS_CONN_URL", "redis://cache")

    with pytest.raises(RuntimeError):
        CombinedConfig.get_env_vars()

    # Conflict within a single class when two prefixes produce same variable after stripping.
    _clear_related_env(monkeypatch)
    monkeypatch.setenv("ZENML_DB_CONN_URL", "postgresql://db")
    monkeypatch.setenv("ZENML_CONN_URL", "postgresql://global")

    with pytest.raises(RuntimeError):
        TwoPrefixConfig.get_env_vars()

    # Missing required fields -> Pydantic validation error (type depends on pydantic version).
    _clear_related_env(monkeypatch)
    # CombinedConfig requires both conn_url and redis_url; only provide one.
    monkeypatch.setenv("ZENML_DB_CONN_URL", "postgresql://db")

    with pytest.raises(Exception):
        CombinedConfig.load_from_env()
