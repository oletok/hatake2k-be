from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os


class Settings(BaseSettings):
    """アプリケーション設定"""
    
    # データベース設定
    database_url: str = Field(
        default="postgresql://hatake_user:hatake_password@localhost:5432/hatake",
        env="DATABASE_URL",
        description="PostgreSQL データベースURL"
    )
    
    # API設定
    api_title: str = Field(default="Hatake API", description="API タイトル")
    api_version: str = Field(default="1.0.0", description="API バージョン")
    api_description: str = Field(default="農作物管理API", description="API 説明")
    
    # サーバー設定
    host: str = Field(default="0.0.0.0", env="HOST", description="サーバーホスト")
    port: int = Field(default=8000, env="PORT", description="サーバーポート")
    debug: bool = Field(default=False, env="DEBUG", description="デバッグモード")
    
    # ログ設定
    log_level: str = Field(default="INFO", env="LOG_LEVEL", description="ログレベル")
    log_file: Optional[str] = Field(default=None, env="LOG_FILE", description="ログファイルパス")
    
    # データ設定
    data_dir: str = Field(default="_data", env="DATA_DIR", description="データディレクトリ")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # 余分なフィールドを無視


# グローバル設定インスタンス
settings = Settings()


def get_settings() -> Settings:
    """設定を取得"""
    return settings