from zenml.utils.time_utils import validate_cron_expression


def test_valid_cron_expressions_pass() -> None:
    valid = [
        "* * * * *",
        "*/5 0 * * 1-5",
        "0 12 * * 0",
        "15,30,45 9-17 * * 1-5",
        "0 0 1 1 *",
    ]
    for expr in valid:
        assert validate_cron_expression(expr), f"Expected valid: {expr}"


def test_invalid_cron_expressions_fail() -> None:
    invalid = [
        None,
        "",
        "* * * *",
        "* * * * * *",
        "60 * * * *",
        "* 24 * * *",
        "* * 0 * *",
        "* * * 13 *",
        "* * * * 8",
        "*/0 * * * *",
        "5-3 * * * *",
        "MON * * * *",
        "@daily",
        "15,30,45 9-a * * 1-5",
    ]
    for expr in invalid:
        assert not validate_cron_expression(expr), f"Expected invalid: {expr}"
