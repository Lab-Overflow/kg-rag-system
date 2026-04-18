"""结构化 + OTEL 双通道日志。"""
import sys

from loguru import logger


def configure_logging(level: str = "INFO") -> None:
    logger.remove()
    logger.add(
        sys.stdout,
        level=level,
        serialize=False,
        enqueue=True,
        backtrace=True,
        diagnose=False,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level:<7}</level> | "
            "<cyan>{name}</cyan>:<cyan>{line}</cyan> | {message}"
        ),
    )
    # JSON sink for prod
    logger.add("logs/app.jsonl", level=level, serialize=True, rotation="100 MB", retention=10)
