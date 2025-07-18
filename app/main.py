from fastapi import FastAPI
from contextlib import asynccontextmanager

from .api.crops import router as crops_router
from .api.postal_codes import router as postal_codes_router
from .api.weather_areas import router as weather_areas_router
from .core.database import create_db_and_tables, health_check
from .core.config import settings
from .core.logging import get_logger

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションのライフサイクル管理"""
    # 起動時処理
    logger.info("Hatake API を起動しています...")
    create_db_and_tables()
    logger.info("データベースとテーブルを初期化しました")
    
    yield
    
    # 終了時処理
    logger.info("Hatake API を終了しています...")


app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description,
    lifespan=lifespan
)

# API ルーターを追加
app.include_router(crops_router)
app.include_router(postal_codes_router)
app.include_router(weather_areas_router)


@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "message": "Hatake API is running",
        "version": settings.api_version,
        "docs_url": "/docs"
    }


@app.get("/health")
async def health_check_endpoint():
    """ヘルスチェックエンドポイント"""
    db_healthy = health_check()
    
    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "database": "connected" if db_healthy else "disconnected",
        "version": settings.api_version
    }