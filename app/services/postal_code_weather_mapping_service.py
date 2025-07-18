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
        
        # 2. 行政区画レベルの曖昧マッチング（区レベルの問題を解決）
        # 郵便番号の市区町村名から区名を除去して検索
        normalized_postal_city = self._normalize_city_name(postal_code.city)
        
        weather_area = self.session.exec(
            select(WeatherArea).where(
                WeatherArea.prefecture == postal_code.prefecture,
                WeatherArea.city == normalized_postal_city
            )
        ).first()
        
        if weather_area:
            return weather_area
        
        # 3. 部分一致検索（郵便番号の市区町村名が気象地域の市区町村名に含まれる）
        weather_area = self.session.exec(
            select(WeatherArea).where(
                WeatherArea.prefecture == postal_code.prefecture,
                WeatherArea.city.like(f"%{postal_code.city}%")
            )
        ).first()
        
        if weather_area:
            return weather_area
        
        # 4. 逆方向の部分一致検索（気象地域の市区町村名が郵便番号の市区町村名に含まれる）
        weather_areas = self.session.exec(
            select(WeatherArea).where(
                WeatherArea.prefecture == postal_code.prefecture
            )
        ).all()
        
        for wa in weather_areas:
            if wa.city in postal_code.city:
                return wa
        
        # 5. 正規化された気象地域名での逆方向検索
        for wa in weather_areas:
            normalized_weather_city = self._normalize_city_name(wa.city)
            if normalized_weather_city == normalized_postal_city:
                return wa
        
        # 6. 政令指定都市の地域別マッピング（東部/西部/北部/南部）
        if normalized_postal_city in ['仙台市', '静岡市', '浜松市', '札幌市', '横浜市', '川崎市', '相模原市', '新潟市', '名古屋市', '京都市', '大阪市', '堺市', '神戸市', '岡山市', '広島市', '北九州市', '福岡市', '熊本市']:
            region_match = self._find_regional_weather_area(postal_code.city, weather_areas)
            if region_match:
                return region_match
        
        # 7. 郡名を含む市区町村名のマッピング（郡以前の文字列を削除）
        if '郡' in postal_code.city:
            simplified_city = self._remove_county_prefix(postal_code.city)
            if simplified_city:
                # 完全一致を先に試す
                weather_area = self.session.exec(
                    select(WeatherArea).where(
                        WeatherArea.prefecture == postal_code.prefecture,
                        WeatherArea.city == simplified_city
                    )
                ).first()
                
                if weather_area:
                    return weather_area
                
                # 部分一致を試す（郡名削除後の市区町村名が天気エリアに含まれる）
                weather_area = self.session.exec(
                    select(WeatherArea).where(
                        WeatherArea.prefecture == postal_code.prefecture,
                        WeatherArea.city.like(f'%{simplified_city}%')
                    )
                ).first()
                
                if weather_area:
                    return weather_area
        
        # 8. 文字表記の正規化マッピング（「ケ」「ヶ」の統一）
        normalized_postal_city = self._normalize_character_variants(postal_code.city)
        if normalized_postal_city != postal_code.city:
            weather_area = self.session.exec(
                select(WeatherArea).where(
                    WeatherArea.prefecture == postal_code.prefecture,
                    WeatherArea.city == normalized_postal_city
                )
            ).first()
            
            if weather_area:
                return weather_area
        
        # 9. 対馬市の特殊マッピング（地域名から上対馬/下対馬への振り分け）
        if postal_code.prefecture == '長崎県' and postal_code.city == '対馬市':
            tsushima_mapping = self._map_tsushima_region(postal_code.town, weather_areas)
            if tsushima_mapping:
                return tsushima_mapping
        
        return None
    
    def _normalize_city_name(self, city_name: str) -> str:
        """
        市区町村名を正規化（区レベルの行政区画を除去）
        
        Args:
            city_name: 市区町村名
            
        Returns:
            正規化された市区町村名
        """
        # 政令指定都市の区を除去
        # 例: "札幌市中央区" → "札幌市"
        # 例: "横浜市鶴見区" → "横浜市"
        # 例: "大阪市北区" → "大阪市"
        
        # 市+区のパターンを検出
        import re
        
        # 「○○市○○区」のパターン
        pattern = r'(.+市)(.+区)$'
        match = re.match(pattern, city_name)
        if match:
            return match.group(1)  # 市の部分のみを返す
        
        # 「○○区」のパターン（東京23区など）
        pattern = r'(.+区)$'
        match = re.match(pattern, city_name)
        if match:
            # 東京23区の場合は特別処理が必要だが、
            # 現在の天気エリアデータの構造を確認する必要がある
            return city_name
        
        return city_name
    
    def _find_regional_weather_area(self, postal_city: str, weather_areas: List[WeatherArea]) -> Optional[WeatherArea]:
        """
        政令指定都市の区から地域（東部/西部/北部/南部）を推定してマッピング
        
        Args:
            postal_city: 郵便番号の市区町村名（例: "仙台市宮城野区"）
            weather_areas: 同一都道府県内の天気エリア一覧
            
        Returns:
            対応する天気エリア（見つからない場合はNone）
        """
        import re
        
        # 区名を抽出
        ward_match = re.search(r'(.+市)(.+区)', postal_city)
        if not ward_match:
            return None
        
        city_name = ward_match.group(1)  # 例: "仙台市"
        ward_name = ward_match.group(2)  # 例: "宮城野区"
        
        # 区名から地域を推定するマッピング
        region_mapping = {
            # 仙台市
            '青葉区': '西部', '宮城野区': '東部', '若林区': '東部', '太白区': '西部', '泉区': '西部',
            
            # 静岡市  
            '葵区': '北部', '駿河区': '南部', '清水区': '南部',
            
            # 浜松市
            '中央区': '南部', '東区': '南部', '西区': '南部', '南区': '南部',
            '北区': '北部', '浜北区': '北部', '天竜区': '北部',
            
            # 札幌市
            '中央区': '西部', '北区': '西部', '東区': '東部', '白石区': '東部',
            '豊平区': '西部', '南区': '西部', '西区': '西部', '厚別区': '東部',
            '手稲区': '西部', '清田区': '東部',
            
            # 横浜市（例：一般的な地域分け）
            '鶴見区': '東部', '神奈川区': '東部', '西区': '西部', '中区': '西部',
            '南区': '西部', '保土ヶ谷区': '西部', '磯子区': '東部', '金沢区': '東部',
            '港北区': '北部', '戸塚区': '西部', '港南区': '西部', '旭区': '西部',
            '緑区': '北部', '瀬谷区': '西部', '栄区': '西部', '泉区': '西部',
            '青葉区': '北部', '都筑区': '北部',
        }
        
        expected_region = region_mapping.get(ward_name)
        if not expected_region:
            # マッピングが不明な場合は、最初に見つかった地域を返す
            for wa in weather_areas:
                if city_name in wa.city:
                    return wa
            return None
        
        # 期待される地域名で検索
        for wa in weather_areas:
            if city_name in wa.city and expected_region in wa.city:
                return wa
        
        # 完全一致しない場合は、市名が含まれる最初の天気エリアを返す
        for wa in weather_areas:
            if city_name in wa.city:
                return wa
        
        return None
    
    def _remove_county_prefix(self, city_name: str) -> str:
        """
        市区町村名から郡名を削除
        
        Args:
            city_name: 郡名を含む市区町村名（例: "沙流郡日高町"）
            
        Returns:
            郡名を削除した市区町村名（例: "日高町"）
        """
        import re
        
        # 「○○郡○○町」「○○郡○○村」「○○郡○○市」のパターン
        pattern = r'.+郡(.+[町村市])$'
        match = re.match(pattern, city_name)
        
        if match:
            return match.group(1)  # 郡以降の部分を返す
        
        return None
    
    def _normalize_character_variants(self, city_name: str) -> str:
        """
        市区町村名の文字表記を正規化（「ケ」「ヶ」の統一など）
        
        Args:
            city_name: 市区町村名
            
        Returns:
            正規化された市区町村名
        """
        # 「ケ」→「ヶ」の変換
        normalized = city_name.replace('ケ', 'ヶ')
        
        # その他の文字表記の統一があれば追加
        # 例: 「ヶ」→「ケ」の逆変換や、「ッ」「ツ」等の統一
        
        return normalized
    
    def _map_tsushima_region(self, town_name: str, weather_areas: List[WeatherArea]) -> Optional[WeatherArea]:
        """
        対馬市の町域名から上対馬/下対馬を判定してマッピング
        
        Args:
            town_name: 町域名
            weather_areas: 長崎県内の天気エリア一覧
            
        Returns:
            対応する天気エリア（上対馬または下対馬）
        """
        # 上対馬地域（北部）
        upper_tsushima_towns = [
            '上県町', '上対馬町'
        ]
        
        # 下対馬地域（南部）
        lower_tsushima_towns = [
            '厳原町', '豊玉町', '美津島町', '峰町'
        ]
        
        # 町域名から地域を判定
        for upper_town in upper_tsushima_towns:
            if upper_town in town_name:
                # 上対馬を探す
                for wa in weather_areas:
                    if '上対馬' in wa.city:
                        return wa
                break
        
        for lower_town in lower_tsushima_towns:
            if lower_town in town_name:
                # 下対馬を探す
                for wa in weather_areas:
                    if '下対馬' in wa.city:
                        return wa
                break
        
        # どちらにも該当しない場合は下対馬をデフォルトとする
        for wa in weather_areas:
            if '下対馬' in wa.city:
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