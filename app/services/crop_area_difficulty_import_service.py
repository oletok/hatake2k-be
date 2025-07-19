"""
作物別気象地域難易度インポートサービス
"""
import csv
import os
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

logger = get_logger("crop_area_difficulty_import")


class CropAreaDifficultyImportService:
    """作物別気象地域難易度インポートサービス"""
    
    def __init__(self, session: Session = None):
        self.session = session or get_sync_session()
    
    def import_crop_area_difficulties_from_directory(
        self, 
        directory_path: str = None
    ) -> Dict[str, Any]:
        """
        ディレクトリ内の全作物CSVファイルから気象地域別難易度データをインポート
        
        Args:
            directory_path: CSVファイルが格納されたディレクトリのパス
        
        Returns:
            インポート結果の統計情報
        """
        if directory_path is None:
            directory_path = Path(settings.data_dir) / "crop-area_difficulties"
        
        directory = Path(directory_path)
        
        if not directory.exists():
            logger.error(f"ディレクトリが見つかりません: {directory}")
            raise FileNotFoundError(f"ディレクトリが見つかりません: {directory}")
        
        logger.info(f"作物別気象地域難易度データインポート開始: {directory}")
        
        try:
            csv_files = self._find_crop_difficulty_files(directory)
            stats = self._process_all_crop_files(csv_files)
            
            logger.info(f"インポート完了: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"インポートエラー: {e}")
            raise
    
    def _find_crop_difficulty_files(self, directory: Path) -> List[Path]:
        """作物難易度CSVファイルを検索"""
        csv_files = []
        
        for file_path in directory.glob("*-area_difficulties.csv"):
            if file_path.is_file():
                csv_files.append(file_path)
        
        logger.info(f"発見された作物難易度CSVファイル数: {len(csv_files)}")
        return csv_files
    
    def _process_all_crop_files(self, csv_files: List[Path]) -> Dict[str, Any]:
        """全ての作物CSVファイルを処理"""
        total_files_processed = 0
        total_combinations_created = 0
        total_combinations_updated = 0
        crops_not_found = []
        files_with_errors = []
        
        for csv_file in csv_files:
            try:
                # ファイル名から作物codeを抽出
                crop_code = self._extract_crop_code_from_filename(csv_file.name)
                
                if not crop_code:
                    logger.warning(f"ファイル名から作物codeを抽出できません: {csv_file.name}")
                    continue
                
                # 作物を検索
                crop = self.session.exec(
                    select(Crop).where(Crop.code == crop_code)
                ).first()
                
                if not crop:
                    crops_not_found.append(crop_code)
                    logger.warning(f"作物が見つかりません: {crop_code}")
                    continue
                
                # CSVファイルを処理
                file_stats = self._process_single_crop_file(csv_file, crop)
                
                total_files_processed += 1
                total_combinations_created += file_stats['created']
                total_combinations_updated += file_stats['updated']
                
                logger.info(f"処理完了: {crop_code} -> 作成:{file_stats['created']}, 更新:{file_stats['updated']}")
                
            except Exception as e:
                files_with_errors.append(csv_file.name)
                logger.error(f"ファイル処理エラー {csv_file.name}: {e}")
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
            "total_files_found": len(csv_files),
            "files_processed": total_files_processed,
            "combinations_created": total_combinations_created,
            "combinations_updated": total_combinations_updated,
            "crops_not_found": crops_not_found,
            "files_with_errors": files_with_errors
        }
    
    def _extract_crop_code_from_filename(self, filename: str) -> Optional[str]:
        """ファイル名から作物codeを抽出"""
        # "crop_code-area_difficulties.csv" -> "crop_code"
        if filename.endswith("-area_difficulties.csv"):
            return filename.replace("-area_difficulties.csv", "")
        return None
    
    def _process_single_crop_file(self, csv_file: Path, crop: Crop) -> Dict[str, int]:
        """単一の作物CSVファイルを処理"""
        created_count = 0
        updated_count = 0
        
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            header = next(reader, None)  # ヘッダー行をスキップ
            
            for row_num, row in enumerate(reader, start=2):  # ヘッダー行の次から開始
                try:
                    if len(row) < 4:
                        logger.warning(f"ファイル {csv_file.name} 行 {row_num}: データが不足しています")
                        continue
                    
                    prefecture = row[0].strip()
                    region = row[1].strip()
                    difficulty = int(row[2].strip())
                    reasons_str = row[3].strip()
                    
                    if not prefecture or not region:
                        logger.warning(f"ファイル {csv_file.name} 行 {row_num}: 都道府県名または区分が空です")
                        continue
                    
                    # 気象地域を検索
                    weather_area = self._find_weather_area(prefecture, region)
                    if not weather_area:
                        logger.warning(f"気象地域が見つかりません: {prefecture} {region}")
                        continue
                    
                    # "|"区切りの理由を配列に変換
                    reasons = [reason.strip() for reason in reasons_str.split("|") if reason.strip()]
                    
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
                    
                except ValueError as e:
                    logger.error(f"ファイル {csv_file.name} 行 {row_num}: 難易度の値が不正です: {row[2]} - {e}")
                    continue
                except Exception as e:
                    logger.error(f"ファイル {csv_file.name} 行 {row_num} の処理エラー: {e}")
                    continue
        
        return {
            "created": created_count,
            "updated": updated_count
        }
    
    def _find_weather_area(self, prefecture: str, region: str) -> Optional[WeatherArea]:
        """都道府県と区分で気象地域を検索"""
        # 完全一致検索
        weather_area = self.session.exec(
            select(WeatherArea).where(
                WeatherArea.prefecture == prefecture,
                WeatherArea.region == region
            )
        ).first()
        
        return weather_area
    
    def get_import_stats(self) -> Dict[str, Any]:
        """インポート統計情報を取得"""
        try:
            # 総組み合わせ数
            total_combinations = len(self.session.exec(select(CropWeatherArea)).all())
            
            # 作物数と気象地域数
            total_crops = len(self.session.exec(select(Crop)).all())
            total_weather_areas = len(self.session.exec(select(WeatherArea)).all())
            
            # 理論的最大組み合わせ数
            max_combinations = total_crops * total_weather_areas
            
            # 作物別の登録状況
            crop_coverage = {}
            crops = self.session.exec(select(Crop)).all()
            
            for crop in crops:
                crop_combinations = len(self.session.exec(
                    select(CropWeatherArea).where(
                        CropWeatherArea.crop_id == crop.id
                    )
                ).all())
                
                crop_coverage[crop.code] = {
                    "registered_areas": crop_combinations,
                    "coverage_rate": (crop_combinations / total_weather_areas * 100) if total_weather_areas > 0 else 0
                }
            
            return {
                "total_crops": total_crops,
                "total_weather_areas": total_weather_areas,
                "total_combinations": total_combinations,
                "max_possible_combinations": max_combinations,
                "overall_coverage_rate": (total_combinations / max_combinations * 100) if max_combinations > 0 else 0,
                "crop_coverage": crop_coverage
            }
            
        except Exception as e:
            logger.error(f"統計情報取得エラー: {e}")
            raise