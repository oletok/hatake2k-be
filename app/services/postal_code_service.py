import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
from sqlmodel import Session, select, text
from datetime import datetime
import hashlib

from ..models.postal_code import (
    PostalCode, 
    PostalCodeCreate, 
    PostalCodeImportStats,
    PostalCodeSearch,
    PostalCodeWithWeatherArea
)
from ..models.weather_area import WeatherArea
from ..core.database import get_sync_session
from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger("postal_code_service")


class PostalCodeService:
    """郵便番号サービス"""
    
    def __init__(self, session: Session = None):
        self.session = session or get_sync_session()
    
    def import_postal_codes_from_csv(
        self, 
        csv_file_path: str = None,
        data_version: str = None,
        update_existing: bool = False
    ) -> PostalCodeImportStats:
        """
        CSVファイルから郵便番号データをインポート
        
        Args:
            csv_file_path: CSVファイルのパス
            data_version: データバージョン（指定しない場合は自動生成）
            update_existing: 既存データを更新するかどうか
        """
        if csv_file_path is None:
            csv_file_path = Path(settings.data_dir) / "utf_ken_all.csv"
        
        csv_path = Path(csv_file_path)
        
        if not csv_path.exists():
            logger.error(f"CSVファイルが見つかりません: {csv_path}")
            raise FileNotFoundError(f"CSVファイルが見つかりません: {csv_path}")
        
        # データバージョンを自動生成（ファイルのハッシュ値）
        if data_version is None:
            data_version = self._generate_data_version(csv_path)
        
        logger.info(f"郵便番号データインポート開始: {csv_path} (version: {data_version})")
        
        # 既存データバージョンをチェック
        existing_version = self._get_current_data_version()
        if existing_version == data_version and not update_existing:
            logger.info(f"データバージョン {data_version} は既にインポート済みです")
            return PostalCodeImportStats(
                total_processed=0,
                created=0,
                updated=0,
                skipped=0,
                errors=0,
                data_version=data_version,
                import_time=datetime.now()
            )
        
        try:
            postal_codes = self._read_postal_codes_from_csv(csv_path, data_version)
            stats = self._save_postal_codes_to_database(postal_codes, update_existing)
            
            logger.info(f"インポート完了: {stats}")
            return PostalCodeImportStats(
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
    
    def _read_postal_codes_from_csv(
        self, 
        csv_path: Path, 
        data_version: str
    ) -> List[PostalCodeCreate]:
        """CSVファイルから郵便番号データを読み込み"""
        postal_codes = []
        
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            
            for row_num, row in enumerate(reader, start=1):
                try:
                    if len(row) < 9:
                        logger.warning(f"行 {row_num}: データが不足しています")
                        continue
                    
                    # CSVの構造: 全国地方公共団体コード,旧郵便番号,郵便番号,都道府県名カナ,市区町村名カナ,町域名カナ,都道府県名,市区町村名,町域名,その他...
                    postal_code_raw = row[2].strip().replace('"', '')  # 郵便番号
                    prefecture = row[6].strip().replace('"', '')       # 都道府県名
                    city = row[7].strip().replace('"', '')             # 市区町村名
                    town = row[8].strip().replace('"', '')             # 町域名
                    
                    # 郵便番号の形式チェック（7桁）
                    if len(postal_code_raw) != 7 or not postal_code_raw.isdigit():
                        logger.warning(f"行 {row_num}: 郵便番号の形式が不正です: {postal_code_raw}")
                        continue
                    
                    # 必須フィールドチェック
                    if not prefecture or not city:
                        logger.warning(f"行 {row_num}: 都道府県名または市区町村名が空です")
                        continue
                    
                    postal_code_data = PostalCodeCreate(
                        postal_code=postal_code_raw,
                        prefecture=prefecture,
                        city=city,
                        town=town or "",  # 町域名は空の場合もある
                        data_version=data_version
                    )
                    
                    postal_codes.append(postal_code_data)
                    
                except Exception as e:
                    logger.error(f"行 {row_num} の読み込みエラー: {e}")
                    continue
        
        logger.info(f"CSVから {len(postal_codes)} 件のデータを読み込みました")
        return postal_codes
    
    def _save_postal_codes_to_database(
        self, 
        postal_codes: List[PostalCodeCreate], 
        update_existing: bool = False
    ) -> Dict[str, Any]:
        """郵便番号データをデータベースに保存"""
        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        # 既存データの削除（更新モードの場合）
        if update_existing:
            self._clear_existing_data()
        
        # バッチサイズを設定（大量データ対応）
        batch_size = 1000
        batch_data = []
        
        for postal_code_data in postal_codes:
            try:
                # 既存データチェック（更新モードでない場合）
                if not update_existing:
                    existing = self.session.exec(
                        select(PostalCode).where(
                            PostalCode.postal_code == postal_code_data.postal_code,
                            PostalCode.prefecture == postal_code_data.prefecture,
                            PostalCode.city == postal_code_data.city,
                            PostalCode.town == postal_code_data.town
                        )
                    ).first()
                    
                    if existing:
                        skipped_count += 1
                        continue
                
                # データを準備
                postal_code = PostalCode(
                    postal_code=postal_code_data.postal_code,
                    prefecture=postal_code_data.prefecture,
                    city=postal_code_data.city,
                    town=postal_code_data.town,
                    data_version=postal_code_data.data_version
                )
                
                batch_data.append(postal_code)
                
                # バッチサイズに達したら保存
                if len(batch_data) >= batch_size:
                    self._save_batch(batch_data)
                    created_count += len(batch_data)
                    batch_data = []
                    
            except Exception as e:
                logger.error(f"郵便番号 {postal_code_data.postal_code} の保存エラー: {e}")
                error_count += 1
                continue
        
        # 残りのデータを保存
        if batch_data:
            self._save_batch(batch_data)
            created_count += len(batch_data)
        
        return {
            "total_processed": len(postal_codes),
            "created": created_count,
            "updated": updated_count,
            "skipped": skipped_count,
            "errors": error_count
        }
    
    def _save_batch(self, batch_data: List[PostalCode]) -> None:
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
            self.session.exec(text("DELETE FROM postal_codes"))
            self.session.commit()
            logger.info("既存の郵便番号データを削除しました")
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
                select(PostalCode.data_version)
                .order_by(PostalCode.created_at.desc())
                .limit(1)
            ).first()
            return result
        except Exception:
            return None
    
    def search_postal_codes(
        self, 
        search_params: PostalCodeSearch,
        limit: int = 100
    ) -> List[PostalCode]:
        """郵便番号検索"""
        try:
            statement = select(PostalCode)
            
            if search_params.postal_code:
                statement = statement.where(
                    PostalCode.postal_code.ilike(f"{search_params.postal_code}%")
                )
            
            if search_params.prefecture:
                statement = statement.where(
                    PostalCode.prefecture.ilike(f"%{search_params.prefecture}%")
                )
            
            if search_params.city:
                statement = statement.where(
                    PostalCode.city.ilike(f"%{search_params.city}%")
                )
            
            if search_params.town:
                statement = statement.where(
                    PostalCode.town.ilike(f"%{search_params.town}%")
                )
            
            statement = statement.limit(limit)
            results = self.session.exec(statement).all()
            
            logger.info(f"郵便番号検索結果: {len(results)} 件")
            return results
            
        except Exception as e:
            logger.error(f"郵便番号検索エラー: {e}")
            raise
    
    def search_postal_codes_with_weather_area(
        self, 
        search_params: PostalCodeSearch,
        limit: int = 100
    ) -> List[PostalCodeWithWeatherArea]:
        """気象地域情報を含む郵便番号検索"""
        try:
            from sqlmodel import select
            from sqlalchemy.orm import selectinload
            
            statement = select(PostalCode).options(selectinload(PostalCode.weather_area))
            
            if search_params.postal_code:
                statement = statement.where(
                    PostalCode.postal_code.ilike(f"{search_params.postal_code}%")
                )
            
            if search_params.prefecture:
                statement = statement.where(
                    PostalCode.prefecture.ilike(f"%{search_params.prefecture}%")
                )
            
            if search_params.city:
                statement = statement.where(
                    PostalCode.city.ilike(f"%{search_params.city}%")
                )
            
            if search_params.town:
                statement = statement.where(
                    PostalCode.town.ilike(f"%{search_params.town}%")
                )
            
            statement = statement.limit(limit)
            results = self.session.exec(statement).all()
            
            # PostalCodeWithWeatherAreaに変換
            postal_codes_with_weather = []
            for postal_code in results:
                postal_data = PostalCodeWithWeatherArea(
                    id=postal_code.id,
                    postal_code=postal_code.postal_code,
                    prefecture=postal_code.prefecture,
                    city=postal_code.city,
                    town=postal_code.town,
                    weather_area_id=postal_code.weather_area_id,
                    data_version=postal_code.data_version,
                    created_at=postal_code.created_at,
                    updated_at=postal_code.updated_at,
                    weather_area=postal_code.weather_area
                )
                postal_codes_with_weather.append(postal_data)
            
            logger.info(f"気象地域情報を含む郵便番号検索結果: {len(postal_codes_with_weather)} 件")
            return postal_codes_with_weather
            
        except Exception as e:
            logger.error(f"気象地域情報を含む郵便番号検索エラー: {e}")
            raise
    
    def get_postal_code_stats(self) -> Dict[str, Any]:
        """郵便番号統計情報を取得"""
        try:
            total_count = len(self.session.exec(select(PostalCode)).all())
            
            # 都道府県別件数
            prefecture_counts = self.session.exec(
                text("""
                SELECT prefecture, COUNT(*) as count 
                FROM postal_codes 
                GROUP BY prefecture 
                ORDER BY count DESC
                """)
            ).all()
            
            current_version = self._get_current_data_version()
            
            return {
                "total_postal_codes": total_count,
                "prefecture_counts": dict(prefecture_counts),
                "current_data_version": current_version,
                "last_updated": self.session.exec(
                    select(PostalCode.updated_at)
                    .order_by(PostalCode.updated_at.desc())
                    .limit(1)
                ).first()
            }
            
        except Exception as e:
            logger.error(f"統計情報取得エラー: {e}")
            raise