"""
作物×気象地域の露地栽培難易度インポートサービス
"""
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
from sqlmodel import Session, select
from datetime import datetime

from ..models.crop import Crop
from ..models.weather_area import WeatherArea
from ..models.crop_weather_area import CropWeatherArea
from ..core.database import get_sync_session
from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger("crop_weather_difficulty_import")


class CropWeatherDifficultyImportService:
    """作物×気象地域の露地栽培難易度インポートサービス"""
    
    def __init__(self, session: Session = None):
        self.session = session or get_sync_session()
    
    def import_outdoor_difficulties_from_csv(
        self, 
        csv_file_path: str = None
    ) -> Dict[str, Any]:
        """
        CSVファイルから露地栽培難易度データをインポート
        全ての気象地域に対して同じ難易度を設定
        
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
        
        logger.info(f"露地栽培難易度データインポート開始: {csv_path}")
        
        try:
            difficulty_data = self._read_outdoor_difficulties_from_csv(csv_path)
            stats = self._create_crop_weather_difficulties(difficulty_data)
            
            logger.info(f"インポート完了: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"インポートエラー: {e}")
            raise
    
    def _read_outdoor_difficulties_from_csv(self, csv_path: Path) -> List[Dict[str, Any]]:
        """CSVファイルから露地栽培難易度データを読み込み"""
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
                    reasons_str = row[2].strip()
                    
                    if not crop_name:
                        logger.warning(f"行 {row_num}: 作物名が空です")
                        continue
                    
                    # "|"区切りの理由を配列に変換
                    reasons = [reason.strip() for reason in reasons_str.split("|") if reason.strip()]
                    
                    difficulties.append({
                        'crop_name': crop_name,
                        'difficulty': difficulty,
                        'reasons': reasons
                    })
                    
                except ValueError as e:
                    logger.error(f"行 {row_num}: 難易度の値が不正です: {row[1]} - {e}")
                    continue
                except Exception as e:
                    logger.error(f"行 {row_num} の読み込みエラー: {e}")
                    continue
        
        logger.info(f"CSVから {len(difficulties)} 件の露地栽培難易度データを読み込みました")
        return difficulties
    
    def _create_crop_weather_difficulties(self, difficulty_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """作物×気象地域の難易度データを作成"""
        created_count = 0
        updated_count = 0
        crop_not_found_count = 0
        error_count = 0
        
        # 全ての気象地域を取得
        weather_areas = self.session.exec(select(WeatherArea)).all()
        logger.info(f"気象地域数: {len(weather_areas)}")
        
        for data in difficulty_data:
            try:
                crop_name = data['crop_name']
                difficulty = data['difficulty']
                reasons = data['reasons']
                
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
                
                if not crop:
                    crop_not_found_count += 1
                    logger.debug(f"作物が見つかりません: {crop_name}")
                    continue
                
                # 全ての気象地域に対して難易度データを作成
                for weather_area in weather_areas:
                    # 既存データをチェック
                    existing = self.session.exec(
                        select(CropWeatherArea).where(
                            CropWeatherArea.crop_id == crop.id,
                            CropWeatherArea.weather_area_id == weather_area.id
                        )
                    ).first()
                    
                    if existing:
                        # 更新
                        existing.difficulty = difficulty
                        existing.difficulty_reasons = reasons
                        existing.updated_at = datetime.now()
                        updated_count += 1
                    else:
                        # 新規作成
                        new_difficulty = CropWeatherArea(
                            crop_id=crop.id,
                            weather_area_id=weather_area.id,
                            difficulty=difficulty,
                            difficulty_reasons=reasons
                        )
                        self.session.add(new_difficulty)
                        created_count += 1
                
                logger.debug(f"処理完了: {crop_name} -> 難易度 {difficulty} ({len(weather_areas)} 地域)")
                
            except Exception as e:
                error_count += 1
                logger.error(f"作物 {data.get('crop_name', 'unknown')} の処理エラー: {e}")
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
            "total_crops_processed": len(difficulty_data),
            "weather_areas_count": len(weather_areas),
            "combinations_created": created_count,
            "combinations_updated": updated_count,
            "crops_not_found": crop_not_found_count,
            "errors": error_count
        }
    
    def get_difficulty_stats(self) -> Dict[str, Any]:
        """作物×気象地域の難易度統計情報を取得"""
        try:
            # 総組み合わせ数
            total_combinations = len(self.session.exec(select(CropWeatherArea)).all())
            
            # 作物数と気象地域数
            total_crops = len(self.session.exec(select(Crop)).all())
            total_weather_areas = len(self.session.exec(select(WeatherArea)).all())
            
            # 理論的最大組み合わせ数
            max_combinations = total_crops * total_weather_areas
            
            # 難易度別の分布
            difficulty_distribution = {}
            combinations = self.session.exec(select(CropWeatherArea)).all()
            
            for combination in combinations:
                difficulty_range = self._get_difficulty_range(combination.difficulty)
                if difficulty_range not in difficulty_distribution:
                    difficulty_distribution[difficulty_range] = 0
                difficulty_distribution[difficulty_range] += 1
            
            return {
                "total_crops": total_crops,
                "total_weather_areas": total_weather_areas,
                "total_combinations": total_combinations,
                "max_possible_combinations": max_combinations,
                "coverage_rate": (total_combinations / max_combinations * 100) if max_combinations > 0 else 0,
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