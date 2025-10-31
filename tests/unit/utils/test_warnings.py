import pytest
from pydantic import ValidationError

from zenml.utils.warnings.base import (
    WarningCategory,
    WarningConfig,
    WarningSeverity,
    WarningVerbosity,
)
from zenml.utils.warnings.controller import WarningController


@pytest.fixture()
def controller() -> WarningController:
    """Provide a clean WarningController for each test.

    We reuse the singleton instance but clear its internal state to ensure test isolation.
    """
    c = WarningController.create()
    # hard reset of internal state
    c._warning_configs.clear()
    c._warning_statistics.clear()
    return c


@pytest.fixture()
def sample_configs() -> dict[str, WarningConfig]:
    """Two simple configs: one normal, one throttled."""
    cfg_normal = WarningConfig(
        code="TEST001",
        category=WarningCategory.USAGE,
        description="Normal (non-throttled) test warning.",
        verbosity=WarningVerbosity.LOW,
        severity=WarningSeverity.MEDIUM,
        is_throttled=False,
    )
    cfg_throttled = WarningConfig(
        code="TEST002",
        category=WarningCategory.USAGE,
        description="Throttled test warning.",
        verbosity=WarningVerbosity.LOW,
        severity=WarningSeverity.MEDIUM,
        is_throttled=True,
    )
    return {"TEST001": cfg_normal, "TEST002": cfg_throttled}


def test_config_validations_accept_valid_values():
    """Valid enum values (or their string forms) should validate and coerce correctly."""
    # direct enums
    cfg = WarningConfig(
        code="VAL001",
        category=WarningCategory.USAGE,
        description="Valid config",
        verbosity=WarningVerbosity.HIGH,
        severity=WarningSeverity.LOW,
        is_throttled=False,
    )
    assert cfg.code == "VAL001"
    assert cfg.category == WarningCategory.USAGE
    assert cfg.verbosity == WarningVerbosity.HIGH
    assert cfg.severity == WarningSeverity.LOW

    # string values (use_enum_values=True allows string inputs matching enum values)
    cfg2 = WarningConfig(
        code="VAL002",
        category="USAGE",
        description="Also valid via strings",
        verbosity="medium",
        severity="high",
        is_throttled=True,
    )
    assert cfg2.category == WarningCategory.USAGE
    assert cfg2.verbosity == WarningVerbosity.MEDIUM
    assert cfg2.severity == WarningSeverity.HIGH
    assert cfg2.is_throttled is True


def test_config_validations_reject_invalid_values():
    """Invalid enum value should raise ValidationError."""
    with pytest.raises(ValidationError):
        WarningConfig(
            code="BAD001",
            category="NOT_A_CATEGORY",
            description="Invalid category value",
            verbosity=WarningVerbosity.LOW,
            severity=WarningSeverity.MEDIUM,
            is_throttled=False,
        )

    with pytest.raises(ValidationError):
        WarningConfig(
            code="BAD002",
            category=WarningCategory.USAGE,
            description="Invalid verbosity value",
            verbosity="very_high",  # invalid
            severity=WarningSeverity.MEDIUM,
            is_throttled=False,
        )

    with pytest.raises(ValidationError):
        WarningConfig(
            code="BAD003",
            category=WarningCategory.USAGE,
            description="Invalid severity value",
            verbosity=WarningVerbosity.LOW,
            severity="critical",  # invalid
            is_throttled=False,
        )


def test_registration_merges_configs(
    controller: WarningController, sample_configs: dict[str, WarningConfig]
):
    controller.register(sample_configs)
    assert controller._warning_configs["TEST001"].code == "TEST001"
    assert controller._warning_configs["TEST002"].is_throttled is True


def test_singleton_instance_is_shared(controller: WarningController):
    another = WarningController()
    assert controller is another


def test_statistics_increment_for_non_throttled(
    controller: WarningController, sample_configs: dict[str, WarningConfig]
):
    controller.register(sample_configs)

    controller.warn(warning_code="TEST001", message="once")
    controller.warn(warning_code="TEST001", message="twice")
    controller.info(warning_code="TEST001", message="thrice")

    assert controller._warning_statistics["TEST001"] == 3


def test_statistics_throttled_only_once(
    controller: WarningController, sample_configs: dict[str, WarningConfig]
):
    controller.register(sample_configs)

    controller.warn(warning_code="TEST002", message="first")
    controller.warn(warning_code="TEST002", message="second")
    controller.info(warning_code="TEST002", message="third")

    assert controller._warning_statistics["TEST002"] == 1


def test_warn_and_info_do_not_break_with_format_kwargs(
    controller: WarningController, sample_configs: dict[str, WarningConfig]
):
    controller.register(sample_configs)

    controller.warn(
        warning_code="TEST001",
        message="something happened",  # no {placeholders}
        foo="unused",
        bar=123,
    )
    controller.info(
        warning_code="TEST001",
        message="another thing",
        baz={"nested": "value"},
    )

    # Side effect: stats should reflect calls; presence of extra kwargs must not raise.
    assert controller._warning_statistics["TEST001"] == 2


def test_unregistered_warning_no_crash_and_no_stats_increment(
    controller: WarningController,
):
    controller.warn(
        warning_code="UNKNOWN", message="should fallback to default"
    )
    controller.info(warning_code="UNKNOWN", message="also fallback")

    assert "UNKNOWN" not in controller._warning_statistics


def test_get_display_message_varies_by_verbosity(
    sample_configs: dict[str, WarningConfig],
):
    from zenml.utils.warnings.controller import WarningController as WC

    module_name = "mod.path"
    line_number = 42

    low = sample_configs["TEST001"].model_copy(
        update={"verbosity": WarningVerbosity.LOW}
    )
    med = sample_configs["TEST001"].model_copy(
        update={"verbosity": WarningVerbosity.MEDIUM}
    )
    high = sample_configs["TEST001"].model_copy(
        update={"verbosity": WarningVerbosity.HIGH}
    )

    msg_low = WC._get_display_message("hello", module_name, line_number, low)
    assert msg_low.startswith(
        "[TEST001](WarningCategory.USAGE)"
    ) or msg_low.startswith("[TEST001](USAGE)")
    assert "hello" in msg_low
    assert "mod.path" not in msg_low and "42" not in msg_low
    assert low.description not in msg_low

    msg_med = WC._get_display_message("hello", module_name, line_number, med)
    assert msg_med.startswith(f"{module_name}:{line_number} ")
    assert "[TEST001]" in msg_med
    assert "hello" in msg_med
    assert med.description not in msg_med

    msg_high = WC._get_display_message("hello", module_name, line_number, high)
    assert "[TEST001]" in msg_high and "hello" in msg_high
    assert "\n" in msg_high
    assert high.description.strip() in msg_high


def test_combined_registries(
    controller: WarningController, sample_configs: dict[str, WarningConfig]
):
    from zenml.utils.warnings.registry import (
        WARNING_CONFIG_REGISTRY,
        WarningCodes,
    )

    controller.register(sample_configs)
    controller.register(WARNING_CONFIG_REGISTRY)

    assert WarningCodes.ZML001.value in controller._warning_configs
    assert "TEST001" in controller._warning_configs

    controller.warn(
        warning_code=WarningCodes.ZML001,
        message="You are warned {name}",
        name="tester",
    )

    assert controller._warning_statistics["ZML001"] >= 1
