from sqlmodel import Session
from app.models.user import User
from app.models.crop import Crop
from app.models.weather_area import WeatherArea
from app.models.postal_code import PostalCode
from app.core.logging import get_logger
import csv
import os
from datetime import datetime

logger = get_logger("seed_service")


class SeedService:
    """データベースのシード処理サービス"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def seed_test_users(self):
        """テストユーザーのシード処理"""
        logger.info("テストユーザーのシード処理を開始")
        
        # 既存のテストユーザーが存在するかチェック
        existing_user = self.session.query(User).filter(
            User.firebase_uid == "test_firebase_uid_12345"
        ).first()
        
        if existing_user:
            logger.info("テストユーザーは既に存在します")
            return existing_user
        
        # テストユーザーを作成
        test_user = User(
            firebase_uid="test_firebase_uid_12345",
            email="maeda@example.com",
            display_name="まえだ",
            bio="よろしく\nやあ",
            weather_area_id=123
        )
        
        self.session.add(test_user)
        self.session.commit()
        self.session.refresh(test_user)
        
        logger.info(f"テストユーザーを作成しました: ID={test_user.id}, Firebase UID={test_user.firebase_uid}")
        return test_user
    
    def seed_crops(self):
        """作物データのシード処理"""
        logger.info("作物データのシード処理を開始")
        
        csv_path = "_data/crops.csv"
        if not os.path.exists(csv_path):
            logger.warning(f"作物データファイルが見つかりません: {csv_path}")
            return []
        
        created_crops = []
        
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # 既存の作物をチェック
                existing_crop = self.session.query(Crop).filter(
                    Crop.code == row['code']
                ).first()
                
                if existing_crop:
                    continue
                
                # 異名をリストに変換
                aliases = row['異名'].split('|') if row['異名'] else []
                
                # 作物を作成
                crop = Crop(
                    code=row['code'],
                    category=row['カテゴリー名'],
                    name=row['作物名'],
                    aliases=aliases,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                
                self.session.add(crop)
                created_crops.append(crop)
        
        self.session.commit()
        logger.info(f"作物データを{len(created_crops)}件作成しました")
        return created_crops
    
    def seed_weather_areas(self):
        """気象地域データのシード処理"""
        logger.info("気象地域データのシード処理を開始")
        
        csv_path = "_data/areas4weather.csv"
        if not os.path.exists(csv_path):
            logger.warning(f"気象地域データファイルが見つかりません: {csv_path}")
            return []
        
        created_areas = []
        
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # 市区町村を分割
                cities = row['市区町村名'].split('|')
                
                for city in cities:
                    # 既存の気象地域をチェック
                    existing_area = self.session.query(WeatherArea).filter(
                        WeatherArea.prefecture == row['都道府県名'],
                        WeatherArea.region == row['区分'],
                        WeatherArea.city == city
                    ).first()
                    
                    if existing_area:
                        continue
                    
                    # 気象地域を作成
                    weather_area = WeatherArea(
                        prefecture=row['都道府県名'],
                        region=row['区分'],
                        city=city,
                        data_version="seed_v1.0",
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    
                    self.session.add(weather_area)
                    created_areas.append(weather_area)
        
        self.session.commit()
        logger.info(f"気象地域データを{len(created_areas)}件作成しました")
        return created_areas
    
    def seed_postal_codes(self):
        """郵便番号データのシード処理"""
        logger.info("郵便番号データのシード処理を開始")
        
        csv_path = "_data/utf_ken_all.csv"
        if not os.path.exists(csv_path):
            logger.warning(f"郵便番号データファイルが見つかりません: {csv_path}")
            return []
        
        created_codes = []
        processed_count = 0
        
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                processed_count += 1
                
                # 1000件ごとにログ出力
                if processed_count % 1000 == 0:
                    logger.info(f"郵便番号データを{processed_count}件処理中...")
                
                # 既存の郵便番号をチェック
                postal_code = row[2]
                existing_code = self.session.query(PostalCode).filter(
                    PostalCode.postal_code == postal_code
                ).first()
                
                if existing_code:
                    continue
                
                # 郵便番号を作成
                postal_code_obj = PostalCode(
                    postal_code=postal_code,
                    prefecture=row[6],
                    city=row[7],
                    town=row[8],
                    data_version="seed_v1.0",
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                
                self.session.add(postal_code_obj)
                created_codes.append(postal_code_obj)
                
                # 100件ごとにコミット
                if len(created_codes) % 100 == 0:
                    self.session.commit()
        
        # 最後のコミット
        self.session.commit()
        logger.info(f"郵便番号データを{len(created_codes)}件作成しました")
        return created_codes
    
    def seed_all(self):
        """全てのシード処理を実行"""
        logger.info("全てのシード処理を開始")
        
        # テストユーザーのシード
        test_user = self.seed_test_users()
        
        # 作物データのシード
        crops = self.seed_crops()
        
        # 気象地域データのシード
        weather_areas = self.seed_weather_areas()
        
        # 郵便番号データのシード
        postal_codes = self.seed_postal_codes()
        
        logger.info("全てのシード処理が完了しました")
        return {
            "test_user": test_user,
            "crops": len(crops),
            "weather_areas": len(weather_areas),
            "postal_codes": len(postal_codes)
        }