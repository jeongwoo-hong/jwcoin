"""
로깅 설정
"""
import logging
import sys
from datetime import datetime


def setup_logger(name: str = "us_stock", level: str = "INFO") -> logging.Logger:
    """로거 설정"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # 이미 핸들러가 있으면 추가하지 않음
    if logger.handlers:
        return logger

    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # 파일 핸들러
    file_handler = logging.FileHandler(
        f"us_stock_trader_{datetime.now().strftime('%Y%m%d')}.log"
    )
    file_handler.setLevel(logging.DEBUG)

    # 포맷터
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "us_stock") -> logging.Logger:
    """로거 가져오기"""
    return logging.getLogger(name)