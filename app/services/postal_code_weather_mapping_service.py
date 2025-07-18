"""
郵便番号と気象地域のマッピングサービス
"""
from typing import Optional, List, Dict, Any
from sqlmodel import Session, select
from ..models.postal_code import PostalCode
from ..models.weather_area import WeatherArea
from ..core.database import get_sync_session
from ..core.logging import get_logger

logger = get_logger("postal_code_weather_mapping")


class PostalCodeWeatherMappingService:
    """郵便番号と気象地域のマッピングサービス"""
    
    def __init__(self, session: Session = None):
        self.session = session or get_sync_session()
    
    def map_postal_codes_to_weather_areas(self) -> Dict[str, Any]:
        """
        郵便番号データに気象地域をマッピング
        
        Returns:
            マッピング結果の統計情報
        """
        logger.info("郵便番号と気象地域のマッピングを開始します")
        
        # 未マッピングの郵便番号を取得
        unmapped_postal_codes = self.session.exec(
            select(PostalCode).where(PostalCode.weather_area_id.is_(None))
        ).all()
        
        logger.info(f"未マッピングの郵便番号: {len(unmapped_postal_codes)} 件")
        
        mapped_count = 0
        not_found_count = 0
        error_count = 0
        
        # バッチ処理
        batch_size = 100
        for i in range(0, len(unmapped_postal_codes), batch_size):
            batch = unmapped_postal_codes[i:i + batch_size]
            
            for postal_code in batch:
                try:
                    # 都道府県と市区町村名で気象地域を検索
                    weather_area = self._find_weather_area_for_postal_code(postal_code)
                    
                    if weather_area:
                        postal_code.weather_area_id = weather_area.id
                        mapped_count += 1
                    else:
                        not_found_count += 1
                        logger.debug(f"気象地域が見つかりません: {postal_code.prefecture} {postal_code.city}")
                        
                except Exception as e:
                    error_count += 1
                    logger.error(f"マッピングエラー: {postal_code.postal_code} - {e}")
                    continue
            
            # バッチごとにコミット
            try:
                self.session.commit()
                logger.info(f"バッチ処理完了: {i//batch_size + 1} / {(len(unmapped_postal_codes) + batch_size - 1) // batch_size}")
            except Exception as e:
                logger.error(f"バッチコミットエラー: {e}")
                self.session.rollback()
                error_count += len(batch)
        
        result = {
            "total_processed": len(unmapped_postal_codes),
            "mapped": mapped_count,
            "not_found": not_found_count,
            "errors": error_count
        }
        
        logger.info(f"マッピング完了: {result}")
        return result
    
    def _find_weather_area_for_postal_code(self, postal_code: PostalCode) -> Optional[WeatherArea]:
        """
        郵便番号に対応する気象地域を検索
        
        Args:
            postal_code: 郵便番号オブジェクト
            
        Returns:
            対応する気象地域（見つからない場合はNone）
        """
        # 1. 完全一致検索（都道府県 + 市区町村名）
        weather_area = self.session.exec(
            select(WeatherArea).where(
                WeatherArea.prefecture == postal_code.prefecture,
                WeatherArea.city == postal_code.city
            )
        ).first()
        
        if weather_area:
            return weather_area
        
        # 2. 部分一致検索（郵便番号の市区町村名が気象地域の市区町村名に含まれる）
        weather_area = self.session.exec(
            select(WeatherArea).where(
                WeatherArea.prefecture == postal_code.prefecture,
                WeatherArea.city.like(f"%{postal_code.city}%")
            )
        ).first()
        
        if weather_area:
            return weather_area
        
        # 3. 逆方向の部分一致検索（気象地域の市区町村名が郵便番号の市区町村名に含まれる）
        weather_areas = self.session.exec(
            select(WeatherArea).where(
                WeatherArea.prefecture == postal_code.prefecture
            )
        ).all()
        
        for wa in weather_areas:
            if wa.city in postal_code.city:
                return wa
        
        return None
    
    def get_mapping_statistics(self) -> Dict[str, Any]:
        """マッピング統計情報を取得"""
        try:
            total_postal_codes = len(self.session.exec(select(PostalCode)).all())
            mapped_postal_codes = len(self.session.exec(
                select(PostalCode).where(PostalCode.weather_area_id.is_not(None))
            ).all())
            
            return {
                "total_postal_codes": total_postal_codes,
                "mapped_postal_codes": mapped_postal_codes,
                "unmapped_postal_codes": total_postal_codes - mapped_postal_codes,
                "mapping_rate": (mapped_postal_codes / total_postal_codes * 100) if total_postal_codes > 0 else 0
            }
        except Exception as e:
            logger.error(f"統計情報取得エラー: {e}")
            raise
    
    def reset_mapping(self) -> Dict[str, Any]:
        """
        全ての郵便番号のマッピングをリセット（危険操作）
        
        Returns:
            リセット結果
        """
        try:
            updated_count = self.session.exec(
                select(PostalCode).where(PostalCode.weather_area_id.is_not(None))
            ).count()
            
            # 全ての weather_area_id を NULL に設定
            self.session.exec(
                select(PostalCode).where(PostalCode.weather_area_id.is_not(None))
            ).update({"weather_area_id": None})
            
            self.session.commit()
            
            logger.warning(f"マッピングをリセットしました: {updated_count} 件")
            
            return {
                "reset_count": updated_count,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"マッピングリセットエラー: {e}")
            self.session.rollback()
            raise