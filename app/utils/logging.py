# app/utils/logging.py
import logging
from app.config import settings

def get_logger(name: str) -> logging.Logger:
    """
    Makes a logger that prints nice timestamps to your terminal.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(settings.log_level)
        handler = logging.StreamHandler()
        handler.setLevel(settings.log_level)
        formatter = logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger
