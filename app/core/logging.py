import logging
import sys
from pathlib import Path
from typing import Optional

from .config import settings


def setup_logging(
    log_level: str = None,
    log_file: Optional[str] = None,
    format_string: str = None
) -> None:
    """ロギング設定"""
    
    # デフォルト値の設定
    log_level = log_level or settings.log_level
    log_file = log_file or settings.log_file
    format_string = format_string or (
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # ログレベルの設定
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # ルートロガーの設定
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # 既存のハンドラーをクリア
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # フォーマッターの作成
    formatter = logging.Formatter(format_string)
    
    # コンソールハンドラーの追加
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # ファイルハンドラーの追加（指定されている場合）
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # アプリケーションログの設定
    app_logger = logging.getLogger("hatake")
    app_logger.setLevel(numeric_level)


def get_logger(name: str) -> logging.Logger:
    """ロガーを取得"""
    return logging.getLogger(f"hatake.{name}")


# デフォルトのロギング設定
setup_logging()