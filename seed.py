#!/usr/bin/env python3
"""
データベースシードスクリプト
"""
from app.core.database import get_session
from app.services.seed_service import SeedService
from app.core.logging import get_logger

logger = get_logger("seed")


def main():
    """メイン処理"""
    logger.info("データベースシード処理を開始")
    
    # セッションを取得
    session = next(get_session())
    
    try:
        # シードサービスを初期化
        seed_service = SeedService(session)
        
        # シード処理を実行
        result = seed_service.seed_all()
        
        logger.info("データベースシード処理が完了しました")
        
        # 結果を出力
        print("=== シード処理結果 ===")
        for key, value in result.items():
            if hasattr(value, 'id'):
                print(f"{key}: ID={value.id}")
            else:
                print(f"{key}: {value}")
        
    except Exception as e:
        logger.error(f"シード処理中にエラーが発生しました: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()