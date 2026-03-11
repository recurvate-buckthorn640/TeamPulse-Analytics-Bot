import logging
import sys


class ContextFilter(logging.Filter):
    """
    Ensure common context keys exist so formatters can rely on them.
    """

    def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
        for key in ("correlation_id", "owner_id", "chat_id", "report_id"):
            if not hasattr(record, key):
                setattr(record, key, None)
        return True


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s "
        "correlation_id=%(correlation_id)s owner_id=%(owner_id)s chat_id=%(chat_id)s report_id=%(report_id)s "
        "%(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(handler)
    root.addFilter(ContextFilter())

