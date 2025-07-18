from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlmodel import Session
from typing import List, Optional, Dict, Any

from ..models.postal_code import (
    PostalCode, 
    PostalCodeRead, 
    PostalCodeSearch,
    PostalCodeImportStats,
    PostalCodeWithWeatherArea
)
from ..core.database import get_session
from ..services.postal_code_service import PostalCodeService
from ..services.postal_code_weather_mapping_service import PostalCodeWeatherMappingService
from ..core.logging import get_logger

router = APIRouter(prefix="/postal-codes", tags=["postal-codes"])
logger = get_logger("postal_codes_api")


def get_postal_code_service(session: Session = Depends(get_session)) -> PostalCodeService:
    """郵便番号サービスを取得"""
    return PostalCodeService(session)


def get_mapping_service(session: Session = Depends(get_session)) -> PostalCodeWeatherMappingService:
    """郵便番号気象地域マッピングサービスを取得"""
    return PostalCodeWeatherMappingService(session)


@router.get("/search", response_model=List[PostalCodeRead])
def search_postal_codes(
    postal_code: Optional[str] = Query(None, description="郵便番号（部分一致）"),
    prefecture: Optional[str] = Query(None, description="都道府県名（部分一致）"),
    city: Optional[str] = Query(None, description="市区町村名（部分一致）"),
    town: Optional[str] = Query(None, description="町域名（部分一致）"),
    limit: int = Query(100, ge=1, le=1000, description="取得件数"),
    postal_service: PostalCodeService = Depends(get_postal_code_service)
):
    """郵便番号検索"""
    logger.info(f"郵便番号検索: postal_code={postal_code}, prefecture={prefecture}, city={city}, town={town}")
    
    search_params = PostalCodeSearch(
        postal_code=postal_code,
        prefecture=prefecture,
        city=city,
        town=town
    )
    
    return postal_service.search_postal_codes(search_params, limit)


@router.get("/code/{postal_code}", response_model=List[PostalCodeRead])
def get_postal_code(
    postal_code: str,
    postal_service: PostalCodeService = Depends(get_postal_code_service)
):
    """郵便番号で住所を取得"""
    logger.info(f"郵便番号取得: {postal_code}")
    
    # 郵便番号の形式チェック
    if len(postal_code) != 7 or not postal_code.isdigit():
        raise HTTPException(
            status_code=400, 
            detail="郵便番号は7桁の数字で入力してください"
        )
    
    search_params = PostalCodeSearch(postal_code=postal_code)
    results = postal_service.search_postal_codes(search_params, limit=100)
    
    if not results:
        raise HTTPException(
            status_code=404, 
            detail=f"郵便番号 '{postal_code}' が見つかりません"
        )
    
    return results


@router.get("/stats/summary", response_model=Dict[str, Any])
def get_postal_code_stats(
    postal_service: PostalCodeService = Depends(get_postal_code_service)
):
    """郵便番号統計情報を取得"""
    logger.info("郵便番号統計情報取得")
    return postal_service.get_postal_code_stats()


@router.post("/import", response_model=PostalCodeImportStats)
def import_postal_codes(
    background_tasks: BackgroundTasks,
    data_version: Optional[str] = Query(None, description="データバージョン"),
    update_existing: bool = Query(False, description="既存データを更新するかどうか"),
    postal_service: PostalCodeService = Depends(get_postal_code_service)
):
    """
    郵便番号データをCSVからインポート
    
    注意: 大量データの処理のため、バックグラウンドで実行されます
    """
    logger.info(f"郵便番号インポート開始: version={data_version}, update={update_existing}")
    
    try:
        # バックグラウンドタスクとして実行
        def import_task():
            return postal_service.import_postal_codes_from_csv(
                data_version=data_version,
                update_existing=update_existing
            )
        
        # 実際のインポート処理
        result = import_task()
        
        # バックグラウンドタスクに登録（ログ出力用）
        background_tasks.add_task(
            lambda: logger.info(f"インポート完了: {result}")
        )
        
        return result
        
    except FileNotFoundError as e:
        logger.error(f"CSVファイルが見つかりません: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"インポートエラー: {e}")
        raise HTTPException(status_code=500, detail="インポートに失敗しました")


@router.get("/prefectures/", response_model=List[str])
def get_prefectures(
    postal_service: PostalCodeService = Depends(get_postal_code_service)
):
    """都道府県一覧を取得"""
    logger.info("都道府県一覧取得")
    
    stats = postal_service.get_postal_code_stats()
    prefectures = list(stats.get("prefecture_counts", {}).keys())
    
    return sorted(prefectures)


@router.get("/cities/{prefecture}", response_model=List[str])
def get_cities_by_prefecture(
    prefecture: str,
    postal_service: PostalCodeService = Depends(get_postal_code_service)
):
    """都道府県別の市区町村一覧を取得"""
    logger.info(f"市区町村一覧取得: {prefecture}")
    
    search_params = PostalCodeSearch(prefecture=prefecture)
    results = postal_service.search_postal_codes(search_params, limit=10000)
    
    cities = list(set(result.city for result in results))
    return sorted(cities)


@router.get("/search-with-weather", response_model=List[PostalCodeWithWeatherArea])
def search_postal_codes_with_weather_area(
    postal_code: Optional[str] = Query(None, description="郵便番号（部分一致）"),
    prefecture: Optional[str] = Query(None, description="都道府県名（部分一致）"),
    city: Optional[str] = Query(None, description="市区町村名（部分一致）"),
    town: Optional[str] = Query(None, description="町域名（部分一致）"),
    limit: int = Query(100, ge=1, le=1000, description="取得件数"),
    postal_service: PostalCodeService = Depends(get_postal_code_service)
):
    """気象地域情報を含む郵便番号検索"""
    logger.info(f"気象地域情報を含む郵便番号検索: postal_code={postal_code}, prefecture={prefecture}, city={city}, town={town}")
    
    search_params = PostalCodeSearch(
        postal_code=postal_code,
        prefecture=prefecture,
        city=city,
        town=town
    )
    
    return postal_service.search_postal_codes_with_weather_area(search_params, limit)


@router.post("/map-weather-areas")
def map_postal_codes_to_weather_areas(
    background_tasks: BackgroundTasks,
    mapping_service: PostalCodeWeatherMappingService = Depends(get_mapping_service)
):
    """
    郵便番号データに気象地域をマッピング
    
    注意: 大量データの処理のため、時間がかかる場合があります
    """
    logger.info("郵便番号と気象地域のマッピング開始")
    
    try:
        # バックグラウンドタスクとして実行
        def mapping_task():
            return mapping_service.map_postal_codes_to_weather_areas()
        
        # 実際のマッピング処理
        result = mapping_task()
        
        # バックグラウンドタスクに登録（ログ出力用）
        background_tasks.add_task(
            lambda: logger.info(f"マッピング完了: {result}")
        )
        
        return result
        
    except Exception as e:
        logger.error(f"マッピングエラー: {e}")
        raise HTTPException(status_code=500, detail="マッピングに失敗しました")


@router.get("/mapping-stats")
def get_mapping_statistics(
    mapping_service: PostalCodeWeatherMappingService = Depends(get_mapping_service)
):
    """郵便番号と気象地域のマッピング統計情報を取得"""
    logger.info("マッピング統計情報取得")
    return mapping_service.get_mapping_statistics()