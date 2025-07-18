import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
from sqlmodel import Session, select, text
from datetime import datetime
import hashlib

from ..models.weather_area import (
    WeatherArea,
    WeatherAreaCreate,
    WeatherAreaImportStats,
    WeatherAreaSearch
)
from ..core.database import get_sync_session
from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger("weather_area_service")


class WeatherAreaService:
    """気象地域サービス"""
    
    def __init__(self, session: Session = None):
        self.session = session or get_sync_session()
    
    def import_weather_areas_from_csv(
        self,
        csv_file_path: str = None,
        data_version: str = None,
        update_existing: bool = False
    ) -> WeatherAreaImportStats:
        """
        CSVファイルから気象地域データをインポート
        
        Args:
            csv_file_path: CSVファイルのパス
            data_version: データバージョン（指定しない場合は自動生成）
            update_existing: 既存データを更新するかどうか
        """
        if csv_file_path is None:
            csv_file_path = Path(settings.data_dir) / "areas4weather.csv"
        
        csv_path = Path(csv_file_path)
        
        if not csv_path.exists():
            logger.error(f"CSVファイルが見つかりません: {csv_path}")
            raise FileNotFoundError(f"CSVファイルが見つかりません: {csv_path}")
        
        # データバージョンを自動生成（ファイルのハッシュ値）
        if data_version is None:
            data_version = self._generate_data_version(csv_path)
        
        logger.info(f"気象地域データインポート開始: {csv_path} (version: {data_version})")
        
        # 既存データバージョンをチェック
        existing_version = self._get_current_data_version()
        if existing_version == data_version and not update_existing:
            logger.info(f"データバージョン {data_version} は既にインポート済みです")
            return WeatherAreaImportStats(
                total_processed=0,
                created=0,
                updated=0,
                skipped=0,
                errors=0,
                data_version=data_version,
                import_time=datetime.now()
            )
        
        try:
            weather_areas = self._read_weather_areas_from_csv(csv_path, data_version)
            stats = self._save_weather_areas_to_database(weather_areas, update_existing)
            
            logger.info(f"インポート完了: {stats}")
            return WeatherAreaImportStats(
                total_processed=stats['total_processed'],
                created=stats['created'],
                updated=stats['updated'],
                skipped=stats['skipped'],
                errors=stats['errors'],
                data_version=data_version,
                import_time=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"インポートエラー: {e}")
            raise
    
    def _read_weather_areas_from_csv(
        self,
        csv_path: Path,
        data_version: str
    ) -> List[WeatherAreaCreate]:
        """CSVファイルから気象地域データを読み込み"""
        weather_areas = []
        
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            next(reader)  # ヘッダー行をスキップ
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    if len(row) < 3:
                        logger.warning(f"行 {row_num}: データが不足しています")
                        continue
                    
                    # CSVの構造: 都道府県名, 区分, 市区町村名（パイプ区切り）
                    prefecture = row[0].strip()
                    region = row[1].strip()
                    cities_str = row[2].strip()
                    
                    # 必須フィールドチェック
                    if not prefecture or not region or not cities_str:
                        logger.warning(f"行 {row_num}: 必須フィールドが空です")
                        continue
                    
                    # 市区町村名をパイプで分割
                    cities = [city.strip() for city in cities_str.split('|')]
                    
                    # 各市区町村について個別のレコードを作成
                    for city in cities:
                        if not city:
                            continue
                        
                        weather_area_data = WeatherAreaCreate(
                            prefecture=prefecture,
                            region=region,
                            city=city,
                            data_version=data_version
                        )
                        
                        weather_areas.append(weather_area_data)
                        
                except Exception as e:
                    logger.error(f"行 {row_num} の読み込みエラー: {e}")
                    continue
        
        logger.info(f"CSVから {len(weather_areas)} 件のデータを読み込みました")
        return weather_areas
    
    def _save_weather_areas_to_database(
        self,
        weather_areas: List[WeatherAreaCreate],
        update_existing: bool = False
    ) -> Dict[str, Any]:
        """気象地域データをデータベースに保存"""
        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        # 既存データの削除（更新モードの場合）
        if update_existing:
            self._clear_existing_data()
        
        # バッチサイズを設定
        batch_size = 500
        batch_data = []
        
        for weather_area_data in weather_areas:
            try:
                # 既存データチェック（更新モードでない場合）
                if not update_existing:
                    existing = self.session.exec(
                        select(WeatherArea).where(
                            WeatherArea.prefecture == weather_area_data.prefecture,
                            WeatherArea.region == weather_area_data.region,
                            WeatherArea.city == weather_area_data.city
                        )
                    ).first()
                    
                    if existing:
                        skipped_count += 1
                        continue
                
                # データを準備
                weather_area = WeatherArea(
                    prefecture=weather_area_data.prefecture,
                    region=weather_area_data.region,
                    city=weather_area_data.city,
                    data_version=weather_area_data.data_version
                )
                
                batch_data.append(weather_area)
                
                # バッチサイズに達したら保存
                if len(batch_data) >= batch_size:
                    self._save_batch(batch_data)
                    created_count += len(batch_data)
                    batch_data = []
                    
            except Exception as e:
                logger.error(f"気象地域 {weather_area_data.prefecture}-{weather_area_data.city} の保存エラー: {e}")
                error_count += 1
                continue
        
        # 残りのデータを保存
        if batch_data:
            self._save_batch(batch_data)
            created_count += len(batch_data)
        
        return {
            "total_processed": len(weather_areas),
            "created": created_count,
            "updated": updated_count,
            "skipped": skipped_count,
            "errors": error_count
        }
    
    def _save_batch(self, batch_data: List[WeatherArea]) -> None:
        """バッチデータを保存"""
        try:
            self.session.add_all(batch_data)
            self.session.commit()
        except Exception as e:
            logger.error(f"バッチ保存エラー: {e}")
            self.session.rollback()
            raise
    
    def _clear_existing_data(self) -> None:
        """既存データを削除"""
        try:
            self.session.exec(text("DELETE FROM weather_area"))
            self.session.commit()
            logger.info("既存の気象地域データを削除しました")
        except Exception as e:
            logger.error(f"既存データ削除エラー: {e}")
            self.session.rollback()
            raise
    
    def _generate_data_version(self, csv_path: Path) -> str:
        """CSVファイルのハッシュ値からデータバージョンを生成"""
        hash_sha256 = hashlib.sha256()
        with open(csv_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        
        hash_value = hash_sha256.hexdigest()[:16]  # 16桁に短縮
        timestamp = datetime.now().strftime("%Y%m%d")
        return f"{timestamp}_{hash_value}"
    
    def _get_current_data_version(self) -> Optional[str]:
        """現在のデータバージョンを取得"""
        try:
            result = self.session.exec(
                select(WeatherArea.data_version)
                .order_by(WeatherArea.created_at.desc())
                .limit(1)
            ).first()
            return result
        except Exception:
            return None
    
    def search_weather_areas(
        self,
        search_params: WeatherAreaSearch,
        limit: int = 100
    ) -> List[WeatherArea]:
        """気象地域検索"""
        try:
            statement = select(WeatherArea)
            
            if search_params.prefecture:
                statement = statement.where(
                    WeatherArea.prefecture.ilike(f"%{search_params.prefecture}%")
                )
            
            if search_params.region:
                statement = statement.where(
                    WeatherArea.region.ilike(f"%{search_params.region}%")
                )
            
            if search_params.city:
                statement = statement.where(
                    WeatherArea.city.ilike(f"%{search_params.city}%")
                )
            
            statement = statement.limit(limit)
            results = self.session.exec(statement).all()
            
            logger.info(f"気象地域検索結果: {len(results)} 件")
            return results
            
        except Exception as e:
            logger.error(f"気象地域検索エラー: {e}")
            raise
    
    def get_weather_area_stats(self) -> Dict[str, Any]:
        """気象地域統計情報を取得"""
        try:
            total_count = len(self.session.exec(select(WeatherArea)).all())
            
            # 都道府県別件数
            prefecture_counts = self.session.exec(
                text("""
                SELECT prefecture, COUNT(*) as count 
                FROM weather_area 
                GROUP BY prefecture 
                ORDER BY count DESC
                """)
            ).all()
            
            # 地方別件数
            region_counts = self.session.exec(
                text("""
                SELECT region, COUNT(*) as count 
                FROM weather_area 
                GROUP BY region 
                ORDER BY count DESC
                """)
            ).all()
            
            current_version = self._get_current_data_version()
            
            return {
                "total_weather_areas": total_count,
                "prefecture_counts": dict(prefecture_counts),
                "region_counts": dict(region_counts),
                "current_data_version": current_version,
                "last_updated": self.session.exec(
                    select(WeatherArea.updated_at)
                    .order_by(WeatherArea.updated_at.desc())
                    .limit(1)
                ).first()
            }
            
        except Exception as e:
            logger.error(f"統計情報取得エラー: {e}")
            raise