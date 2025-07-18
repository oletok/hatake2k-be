from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from typing import List, Optional

from ..models.crop import Crop, CropRead, CropCreate
from ..core.database import get_session
from ..services.crop_service import CropService
from ..core.logging import get_logger

router = APIRouter(prefix="/crops", tags=["crops"])
logger = get_logger("crops_api")


def get_crop_service(session: Session = Depends(get_session)) -> CropService:
    """作物サービスを取得"""
    return CropService(session)


@router.get("/", response_model=List[CropRead])
def get_crops(
    skip: int = Query(0, ge=0, description="スキップ件数"),
    limit: int = Query(100, ge=1, le=1000, description="取得件数"),
    category: Optional[str] = Query(None, description="カテゴリーフィルター"),
    crop_service: CropService = Depends(get_crop_service)
):
    """作物一覧を取得"""
    logger.info(f"作物一覧取得: skip={skip}, limit={limit}, category={category}")
    return crop_service.get_crops(skip=skip, limit=limit, category=category)


@router.get("/{code}", response_model=CropRead)
def get_crop_by_code(
    code: str,
    crop_service: CropService = Depends(get_crop_service)
):
    """作物コードで作物を取得"""
    logger.info(f"作物取得: code={code}")
    return crop_service.get_crop_by_code(code)


@router.get("/search/", response_model=List[CropRead])
def search_crops(
    q: str = Query(..., min_length=1, description="検索クエリ"),
    limit: int = Query(50, ge=1, le=100, description="取得件数"),
    crop_service: CropService = Depends(get_crop_service)
):
    """作物名・異名で検索"""
    logger.info(f"作物検索: query={q}, limit={limit}")
    return crop_service.search_crops(q, limit)


@router.get("/categories/", response_model=List[str])
def get_crop_categories(crop_service: CropService = Depends(get_crop_service)):
    """作物カテゴリー一覧を取得"""
    logger.info("カテゴリー一覧取得")
    return crop_service.get_categories()




@router.get("/stats/count", response_model=int)
def get_crop_count(crop_service: CropService = Depends(get_crop_service)):
    """作物の総数を取得"""
    logger.info("作物総数取得")
    return crop_service.get_crop_count()