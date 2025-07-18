#!/usr/bin/env python3
"""
FastAPI Console - Rails console equivalent
Usage: python console.py
"""

import sys
from sqlmodel import Session, select
from app.models.crop import Crop
from app.core.database import get_sync_session
from app.services.crop_service import CropService
from app.services.import_service import ImportService
from app.services.postal_code_service import PostalCodeService
from app.services.weather_area_service import WeatherAreaService
from app.core.config import settings
from app.core.logging import get_logger

# ログ設定
logger = get_logger("console")

# データベース接続
session = get_sync_session()
crop_service = CropService(session)
import_service = ImportService(session)
postal_service = PostalCodeService(session)
weather_service = WeatherAreaService(session)

# よく使う関数を定義
def crops_count():
    """作物の総数を取得"""
    return crop_service.get_crop_count()

def crops_by_category(category):
    """カテゴリー別作物一覧"""
    return crop_service.get_crops(category=category)

def search_crops(query):
    """作物名・異名で検索"""
    return crop_service.search_crops(query)

def get_crop(code):
    """作物コードで取得"""
    return crop_service.get_crop_by_code(code)

def categories():
    """カテゴリー一覧"""
    return crop_service.get_categories()

def import_crops():
    """作物データをインポート"""
    return import_service.import_crops_from_csv()

def import_stats():
    """インポート統計情報"""
    return import_service.get_import_stats()

def import_postal_codes():
    """郵便番号データをインポート"""
    return postal_service.import_postal_codes_from_csv()

def postal_stats():
    """郵便番号統計情報"""
    return postal_service.get_postal_code_stats()

def search_postal_codes(query):
    """郵便番号検索"""
    from app.models.postal_code import PostalCodeSearch
    search_params = PostalCodeSearch(postal_code=query)
    return postal_service.search_postal_codes(search_params)

def import_weather_areas():
    """気象地域データをインポート"""
    return weather_service.import_weather_areas_from_csv()

def weather_stats():
    """気象地域統計情報"""
    return weather_service.get_weather_area_stats()

def search_weather_areas(query):
    """気象地域検索"""
    from app.models.weather_area import WeatherAreaSearch
    search_params = WeatherAreaSearch(city=query)
    return weather_service.search_weather_areas(search_params)

# ヘルプ関数
def help_commands():
    """利用可能なコマンド一覧"""
    print("""
FastAPI Console - 利用可能なコマンド:

# 基本操作
crops_count()                    # 作物の総数
categories()                     # カテゴリー一覧
get_crop('komatsuna')           # 作物コード検索
search_crops('トマト')          # 作物名・異名検索
crops_by_category('葉菜類')     # カテゴリー別一覧

# SQLModel操作
session.exec(select(Crop).limit(5)).all()  # 最初の5件
session.exec(select(Crop).where(Crop.category == '果菜類')).all()

# 変数
session  # SQLModel Session
Crop     # 作物モデル
select   # SQLModel select
""")

if __name__ == "__main__":
    print("FastAPI Console - Rails console equivalent")
    print("Type 'help_commands()' for available commands")
    print("Type 'exit()' to quit")
    print("-" * 50)
    
    # IPython があれば使用、なければ標準REPL
    try:
        from IPython import embed
        embed()
    except ImportError:
        import code
        code.interact(local=locals())