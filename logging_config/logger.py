import logging
from logging import Logger
from typing import Optional


def get_logger(name: Optional[str] = None, level: int = logging.INFO) -> Logger:
    """
    Create and return a configured logger that logs to the terminal.
    Ensures handlers are not duplicated on repeated calls.
    """
    logger = logging.getLogger(name if name else __name__)
    logger.setLevel(level)

    # Avoid adding multiple handlers if called multiple times
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)

        formatter = logging.Formatter(
            fmt="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Reduce noisy third-party loggers if needed
        logging.getLogger("selenium").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)

        # Do not propagate to root to avoid duplicate logs
        logger.propagate = False

    return logger 