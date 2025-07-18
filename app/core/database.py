from sqlmodel import SQLModel, Session, create_engine, text
from typing import Generator
import logging

from .config import settings
from .logging import get_logger

logger = get_logger("database")

# データベースエンジンの作成
engine = create_engine(
    settings.database_url,
    echo=settings.debug,  # デバッグ時はSQLログを表示
    pool_pre_ping=True,   # 接続の健全性チェック
    pool_recycle=3600,    # 1時間でコネクションを再作成
)


def create_db_and_tables() -> None:
    """データベースとテーブルを作成"""
    try:
        SQLModel.metadata.create_all(engine)
        logger.info("データベースとテーブルを作成しました")
    except Exception as e:
        logger.error(f"データベース作成エラー: {e}")
        raise


def get_session() -> Generator[Session, None, None]:
    """データベースセッションを取得"""
    with Session(engine) as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"データベースセッションエラー: {e}")
            session.rollback()
            raise
        finally:
            session.close()


def get_sync_session() -> Session:
    """同期セッションを取得（コンソールやスクリプト用）"""
    return Session(engine)


def health_check() -> bool:
    """データベースヘルスチェック"""
    try:
        with Session(engine) as session:
            session.exec(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"データベースヘルスチェック失敗: {e}")
        return False