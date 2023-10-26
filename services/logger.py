import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from settings.config import PROJECT_DIR


def get_logger(name: str = None):
    if not name:
        run_file = sys.argv[0]
        name = os.path.splitext(os.path.basename(run_file))[0]
    logger = logging.getLogger(name)
    file_handler = RotatingFileHandler(
        filename=f'{PROJECT_DIR}/logs/{name}.log',
        maxBytes=1024 * 1024 * 5,  # 5 MB
        backupCount=3,
        encoding='UTF-8',
    )
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] - %(message)s', '%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.setLevel(logging.INFO)
    return logger


logger = get_logger()
