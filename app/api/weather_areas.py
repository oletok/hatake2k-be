from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlmodel import Session
from typing import List, Optional, Dict, Any

from ..models.weather_area import (
    WeatherArea,
    WeatherAreaRead,
    WeatherAreaSearch,
    WeatherAreaImportStats
)
from ..core.database import get_session
from ..services.weather_area_service import WeatherAreaService
from ..core.logging import get_logger

router = APIRouter(prefix="/weather-areas", tags=["weather-areas"])
logger = get_logger("weather_areas_api")


def get_weather_area_service(session: Session = Depends(get_session)) -> WeatherAreaService:
    """気象地域サービスを取得"""
    return WeatherAreaService(session)


@router.get("/search", response_model=List[WeatherAreaRead])
def search_weather_areas(
    prefecture: Optional[str] = Query(None, description="都道府県名（部分一致）"),
    region: Optional[str] = Query(None, description="地方・区分（部分一致）"),
    city: Optional[str] = Query(None, description="市区町村名（部分一致）"),
    limit: int = Query(100, ge=1, le=1000, description="取得件数"),
    weather_service: WeatherAreaService = Depends(get_weather_area_service)
):
    """気象地域検索"""
    logger.info(f"気象地域検索: prefecture={prefecture}, region={region}, city={city}")
    
    search_params = WeatherAreaSearch(
        prefecture=prefecture,
        region=region,
        city=city
    )
    
    return weather_service.search_weather_areas(search_params, limit)


@router.get("/prefectures/", response_model=List[str])
def get_prefectures(
    weather_service: WeatherAreaService = Depends(get_weather_area_service)
):
    """都道府県一覧を取得"""
    logger.info("都道府県一覧取得")
    
    stats = weather_service.get_weather_area_stats()
    prefectures = list(stats.get("prefecture_counts", {}).keys())
    
    return sorted(prefectures)


@router.get("/regions/", response_model=List[str])
def get_regions(
    weather_service: WeatherAreaService = Depends(get_weather_area_service)
):
    """地方・区分一覧を取得"""
    logger.info("地方・区分一覧取得")
    
    stats = weather_service.get_weather_area_stats()
    regions = list(stats.get("region_counts", {}).keys())
    
    return sorted(regions)


@router.get("/regions/{prefecture}", response_model=List[str])
def get_regions_by_prefecture(
    prefecture: str,
    weather_service: WeatherAreaService = Depends(get_weather_area_service)
):
    """都道府県別の地方・区分一覧を取得"""
    logger.info(f"都道府県別地方一覧取得: {prefecture}")
    
    search_params = WeatherAreaSearch(prefecture=prefecture)
    results = weather_service.search_weather_areas(search_params, limit=1000)
    
    regions = list(set(result.region for result in results))
    return sorted(regions)


@router.get("/cities/{prefecture}", response_model=List[str])
def get_cities_by_prefecture(
    prefecture: str,
    region: Optional[str] = Query(None, description="地方・区分での絞り込み"),
    weather_service: WeatherAreaService = Depends(get_weather_area_service)
):
    """都道府県別（および地方別）の市区町村一覧を取得"""
    logger.info(f"都道府県別市区町村一覧取得: {prefecture}, region={region}")
    
    search_params = WeatherAreaSearch(
        prefecture=prefecture,
        region=region
    )
    results = weather_service.search_weather_areas(search_params, limit=10000)
    
    cities = list(set(result.city for result in results))
    return sorted(cities)


@router.get("/cities/{prefecture}/{region}", response_model=List[str])
def get_cities_by_prefecture_and_region(
    prefecture: str,
    region: str,
    weather_service: WeatherAreaService = Depends(get_weather_area_service)
):
    """都道府県・地方別の市区町村一覧を取得"""
    logger.info(f"都道府県・地方別市区町村一覧取得: {prefecture}, {region}")
    
    search_params = WeatherAreaSearch(
        prefecture=prefecture,
        region=region
    )
    results = weather_service.search_weather_areas(search_params, limit=10000)
    
    cities = list(set(result.city for result in results))
    return sorted(cities)


@router.get("/stats/summary", response_model=Dict[str, Any])
def get_weather_area_stats(
    weather_service: WeatherAreaService = Depends(get_weather_area_service)
):
    """気象地域統計情報を取得"""
    logger.info("気象地域統計情報取得")
    return weather_service.get_weather_area_stats()


@router.post("/import", response_model=WeatherAreaImportStats)
def import_weather_areas(
    background_tasks: BackgroundTasks,
    data_version: Optional[str] = Query(None, description="データバージョン"),
    update_existing: bool = Query(False, description="既存データを更新するかどうか"),
    weather_service: WeatherAreaService = Depends(get_weather_area_service)
):
    """
    気象地域データをCSVからインポート
    
    注意: 市区町村名のパイプ区切りを個別レコードに分割してインポートします
    """
    logger.info(f"気象地域インポート開始: version={data_version}, update={update_existing}")
    
    try:
        # バックグラウンドタスクとして実行
        def import_task():
            return weather_service.import_weather_areas_from_csv(
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


@router.get("/weather-regions/", response_model=List[Dict[str, Any]])
def get_weather_regions(
    weather_service: WeatherAreaService = Depends(get_weather_area_service)
):
    """気象地域の階層構造を取得（都道府県 -> 地方 -> 市区町村）"""
    logger.info("気象地域階層構造取得")
    
    # 全データを取得
    all_areas = weather_service.search_weather_areas(WeatherAreaSearch(), limit=10000)
    
    # 階層構造を構築
    regions = {}
    for area in all_areas:
        if area.prefecture not in regions:
            regions[area.prefecture] = {}
        if area.region not in regions[area.prefecture]:
            regions[area.prefecture][area.region] = []
        regions[area.prefecture][area.region].append(area.city)
    
    # レスポンス形式に変換
    result = []
    for prefecture, prefecture_regions in regions.items():
        prefecture_data = {
            "prefecture": prefecture,
            "regions": []
        }
        for region, cities in prefecture_regions.items():
            region_data = {
                "region": region,
                "cities": sorted(cities)
            }
            prefecture_data["regions"].append(region_data)
        result.append(prefecture_data)
    
    return sorted(result, key=lambda x: x["prefecture"])