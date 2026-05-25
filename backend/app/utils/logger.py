# 日志配置

import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)


def setup_logger(name: str = "smart_posture") -> logging.Logger:
    """配置日志：控制台 + 文件轮转"""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # 格式
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 控制台
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    logger.addHandler(console)

    # 文件（10MB × 3 个轮转）
    file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "app.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    return logger


# 全局 logger 实例
logger = setup_logger()
