"""
作物難易度データインポートサービス
"""
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
from sqlmodel import Session, select
from datetime import datetime

from ..models.crop import Crop
from ..core.database import get_sync_session
from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger("crop_difficulty_import")


class CropDifficultyImportService:
    """作物難易度インポートサービス"""
    
    def __init__(self, session: Session = None):
        self.session = session or get_sync_session()
    
    def import_crop_difficulties_from_csv(
        self, 
        csv_file_path: str = None
    ) -> Dict[str, Any]:
        """
        CSVファイルから作物難易度データをインポート
        
        Args:
            csv_file_path: CSVファイルのパス
        
        Returns:
            インポート結果の統計情報
        """
        if csv_file_path is None:
            csv_file_path = Path(settings.data_dir) / "crop_difficulties.csv"
        
        csv_path = Path(csv_file_path)
        
        if not csv_path.exists():
            logger.error(f"CSVファイルが見つかりません: {csv_path}")
            raise FileNotFoundError(f"CSVファイルが見つかりません: {csv_path}")
        
        logger.info(f"作物難易度データインポート開始: {csv_path}")
        
        try:
            difficulty_data = self._read_crop_difficulties_from_csv(csv_path)
            stats = self._update_crops_with_difficulties(difficulty_data)
            
            logger.info(f"インポート完了: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"インポートエラー: {e}")
            raise
    
    def _read_crop_difficulties_from_csv(self, csv_path: Path) -> List[Dict[str, Any]]:
        """CSVファイルから作物難易度データを読み込み"""
        difficulties = []
        
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            header = next(reader)  # ヘッダー行をスキップ
            
            for row_num, row in enumerate(reader, start=2):  # ヘッダー行の次から開始
                try:
                    if len(row) < 3:
                        logger.warning(f"行 {row_num}: データが不足しています")
                        continue
                    
                    crop_name = row[0].strip()
                    difficulty = int(row[1].strip())
                    reason = row[2].strip()
                    
                    if not crop_name:
                        logger.warning(f"行 {row_num}: 作物名が空です")
                        continue
                    
                    difficulties.append({
                        'crop_name': crop_name,
                        'difficulty': difficulty,
                        'reason': reason
                    })
                    
                except ValueError as e:
                    logger.error(f"行 {row_num}: 難易度の値が不正です: {row[1]} - {e}")
                    continue
                except Exception as e:
                    logger.error(f"行 {row_num} の読み込みエラー: {e}")
                    continue
        
        logger.info(f"CSVから {len(difficulties)} 件の難易度データを読み込みました")
        return difficulties
    
    def _update_crops_with_difficulties(self, difficulty_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """作物テーブルに難易度データを更新"""
        updated_count = 0
        not_found_count = 0
        error_count = 0
        
        for data in difficulty_data:
            try:
                crop_name = data['crop_name']
                difficulty = data['difficulty']
                reason = data['reason']
                
                # 作物名で検索（完全一致）
                crop = self.session.exec(
                    select(Crop).where(Crop.name == crop_name)
                ).first()
                
                if not crop:
                    # エイリアス（異名）でも検索
                    crops_with_aliases = self.session.exec(select(Crop)).all()
                    for c in crops_with_aliases:
                        if crop_name in c.get_aliases_list():
                            crop = c
                            break
                
                if crop:
                    # 難易度情報を更新
                    crop.difficulty = difficulty
                    crop.difficulty_reason = reason
                    crop.updated_at = datetime.now()
                    
                    updated_count += 1
                    logger.debug(f"更新: {crop_name} -> 難易度 {difficulty}")
                else:
                    not_found_count += 1
                    logger.debug(f"作物が見つかりません: {crop_name}")
                
            except Exception as e:
                error_count += 1
                logger.error(f"作物 {data.get('crop_name', 'unknown')} の更新エラー: {e}")
                continue
        
        # 変更をコミット
        try:
            self.session.commit()
            logger.info(f"データベースへの更新をコミットしました")
        except Exception as e:
            logger.error(f"コミットエラー: {e}")
            self.session.rollback()
            raise
        
        return {
            "total_processed": len(difficulty_data),
            "updated": updated_count,
            "not_found": not_found_count,
            "errors": error_count
        }
    
    def get_difficulty_stats(self) -> Dict[str, Any]:
        """難易度統計情報を取得"""
        try:
            # 全作物数
            total_crops = len(self.session.exec(select(Crop)).all())
            
            # 難易度が設定された作物数
            crops_with_difficulty = len(self.session.exec(
                select(Crop).where(Crop.difficulty.is_not(None))
            ).all())
            
            # 難易度別の分布
            difficulty_distribution = {}
            crops = self.session.exec(
                select(Crop).where(Crop.difficulty.is_not(None))
            ).all()
            
            for crop in crops:
                difficulty_range = self._get_difficulty_range(crop.difficulty)
                if difficulty_range not in difficulty_distribution:
                    difficulty_distribution[difficulty_range] = 0
                difficulty_distribution[difficulty_range] += 1
            
            return {
                "total_crops": total_crops,
                "crops_with_difficulty": crops_with_difficulty,
                "crops_without_difficulty": total_crops - crops_with_difficulty,
                "coverage_rate": (crops_with_difficulty / total_crops * 100) if total_crops > 0 else 0,
                "difficulty_distribution": difficulty_distribution
            }
            
        except Exception as e:
            logger.error(f"統計情報取得エラー: {e}")
            raise
    
    def _get_difficulty_range(self, difficulty: int) -> str:
        """難易度を範囲で分類"""
        if difficulty <= 10:
            return "超簡単 (1-10)"
        elif difficulty <= 20:
            return "簡単 (11-20)"
        elif difficulty <= 30:
            return "やや簡単 (21-30)"
        elif difficulty <= 40:
            return "普通 (31-40)"
        elif difficulty <= 50:
            return "やや難しい (41-50)"
        elif difficulty <= 60:
            return "難しい (51-60)"
        elif difficulty <= 70:
            return "かなり難しい (61-70)"
        else:
            return "超難しい (71-100)"