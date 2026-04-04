import logging

from zenml.logger import (
    ConsoleFormatter,
    ZenMLLoggingHandler,
    _ZenMLStdoutStream,
    init_logging,
)


def _is_zenml_console_handler(handler: logging.Handler) -> bool:
    return (
        isinstance(handler, logging.StreamHandler)
        and isinstance(getattr(handler, "stream", None), _ZenMLStdoutStream)
        and isinstance(handler.formatter, ConsoleFormatter)
    )


def _is_zenml_handler(handler: logging.Handler) -> bool:
    return _is_zenml_console_handler(handler) or isinstance(
        handler, ZenMLLoggingHandler
    )


def test_init_logging_is_idempotent(monkeypatch):
    monkeypatch.setenv("ZENML_SUPPRESS_LOGS", "true")
    root_logger = logging.getLogger()

    original_handlers = list(root_logger.handlers)
    root_logger.handlers = [
        handler
        for handler in root_logger.handlers
        if not _is_zenml_handler(handler)
    ]

    try:
        init_logging()
        first_count = sum(
            1 for handler in root_logger.handlers if _is_zenml_handler(handler)
        )

        init_logging()
        second_count = sum(
            1 for handler in root_logger.handlers if _is_zenml_handler(handler)
        )

        assert first_count == 2
        assert second_count == 2
    finally:
        root_logger.handlers = original_handlers
