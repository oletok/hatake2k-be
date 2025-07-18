import csv
from pathlib import Path
from typing import List, Dict, Any
from sqlmodel import Session, select

from ..models.crop import Crop, CropCreate
from ..core.database import get_sync_session
from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger("import_service")


class ImportService:
    """データインポートサービス"""
    
    def __init__(self, session: Session = None):
        self.session = session or get_sync_session()
    
    def import_crops_from_csv(self, csv_file_path: str = None) -> Dict[str, Any]:
        """CSVファイルから作物データをインポート"""
        
        if csv_file_path is None:
            csv_file_path = Path(settings.data_dir) / "crops.csv"
        
        csv_path = Path(csv_file_path)
        
        if not csv_path.exists():
            logger.error(f"CSVファイルが見つかりません: {csv_path}")
            raise FileNotFoundError(f"CSVファイルが見つかりません: {csv_path}")
        
        logger.info(f"CSVファイルからインポート開始: {csv_path}")
        
        try:
            crops = self._read_crops_from_csv(csv_path)
            result = self._save_crops_to_database(crops)
            
            logger.info(f"インポート完了: {result}")
            return result
            
        except Exception as e:
            logger.error(f"インポートエラー: {e}")
            raise
    
    def _read_crops_from_csv(self, csv_path: Path) -> List[CropCreate]:
        """CSVファイルから作物データを読み込み"""
        crops = []
        
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    # 異名をパイプ区切りからリストに変換
                    aliases_str = row['異名'].strip()
                    aliases_list = []
                    if aliases_str:
                        aliases_list = [alias.strip() for alias in aliases_str.split('|') if alias.strip()]
                    
                    crop_data = CropCreate(
                        code=row['code'].strip(),
                        category=row['カテゴリー名'].strip(),
                        name=row['作物名'].strip(),
                        aliases=aliases_list
                    )
                    
                    # データ検証
                    if not crop_data.code:
                        logger.warning(f"行 {row_num}: コードが空です")
                        continue
                    
                    if not crop_data.name:
                        logger.warning(f"行 {row_num}: 作物名が空です")
                        continue
                    
                    crops.append(crop_data)
                    
                except Exception as e:
                    logger.error(f"行 {row_num} の読み込みエラー: {e}")
                    continue
        
        logger.info(f"CSVから {len(crops)} 件のデータを読み込みました")
        return crops
    
    def _save_crops_to_database(self, crops: List[CropCreate]) -> Dict[str, Any]:
        """作物データをデータベースに保存"""
        created_count = 0
        skipped_count = 0
        error_count = 0
        
        for crop_data in crops:
            try:
                # 既存データチェック
                existing = self.session.exec(
                    select(Crop).where(Crop.code == crop_data.code)
                ).first()
                
                if existing:
                    logger.debug(f"作物 {crop_data.code} は既に存在します")
                    skipped_count += 1
                    continue
                
                # 新規作成
                crop = Crop(
                    code=crop_data.code,
                    category=crop_data.category,
                    name=crop_data.name,
                    aliases=crop_data.aliases
                )
                
                self.session.add(crop)
                created_count += 1
                
            except Exception as e:
                logger.error(f"作物 {crop_data.code} の保存エラー: {e}")
                error_count += 1
                continue
        
        # 一括コミット
        try:
            self.session.commit()
            logger.info(f"データベースに {created_count} 件を保存しました")
        except Exception as e:
            logger.error(f"データベース保存エラー: {e}")
            self.session.rollback()
            raise
        
        return {
            "total_processed": len(crops),
            "created": created_count,
            "skipped": skipped_count,
            "errors": error_count
        }
    
    def get_import_stats(self) -> Dict[str, Any]:
        """インポート統計情報を取得"""
        try:
            total_crops = len(self.session.exec(select(Crop)).all())
            categories = self.session.exec(select(Crop.category).distinct()).all()
            
            return {
                "total_crops": total_crops,
                "total_categories": len(categories),
                "categories": sorted(categories)
            }
        except Exception as e:
            logger.error(f"統計情報取得エラー: {e}")
            raise
    
    def reset_crops_data(self) -> Dict[str, Any]:
        """作物データをリセット（危険操作）"""
        try:
            deleted_count = self.session.exec(select(Crop)).count()
            
            # 全削除
            self.session.exec("DELETE FROM crop")
            self.session.commit()
            
            logger.warning(f"作物データを全削除しました: {deleted_count} 件")
            
            return {
                "deleted_count": deleted_count,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"データリセットエラー: {e}")
            self.session.rollback()
            raise