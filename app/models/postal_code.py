from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from .weather_area import WeatherArea


class PostalCode(SQLModel, table=True):
    """郵便番号テーブル"""
    
    __tablename__ = "postal_codes"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    postal_code: str = Field(index=True, description="郵便番号7桁")
    prefecture: str = Field(index=True, description="都道府県名")
    city: str = Field(index=True, description="市区町村名")
    town: str = Field(index=True, description="町域丁目番地")
    
    # 気象地域への外部キー
    weather_area_id: Optional[int] = Field(default=None, foreign_key="weather_areas.id")
    
    # メンテナンス用フィールド
    data_version: str = Field(default="", description="データバージョン")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # リレーション
    weather_area: Optional["WeatherArea"] = Relationship(back_populates="postal_codes")
    
    def __repr__(self):
        return f"<PostalCode(postal_code='{self.postal_code}', prefecture='{self.prefecture}')>"


class PostalCodeCreate(SQLModel):
    """郵便番号作成用モデル"""
    
    postal_code: str
    prefecture: str
    city: str
    town: str
    weather_area_id: Optional[int] = None
    data_version: str = ""


class PostalCodeRead(SQLModel):
    """郵便番号読み取り用モデル"""
    
    id: int
    postal_code: str
    prefecture: str
    city: str
    town: str
    weather_area_id: Optional[int]
    data_version: str
    created_at: datetime
    updated_at: datetime


class PostalCodeWithWeatherArea(SQLModel):
    """郵便番号（気象地域情報含む）読み取り用モデル"""
    
    id: int
    postal_code: str
    prefecture: str
    city: str
    town: str
    weather_area_id: Optional[int]
    data_version: str
    created_at: datetime
    updated_at: datetime
    
    # 気象地域情報
    weather_area: Optional["WeatherAreaRead"] = None


class PostalCodeUpdate(SQLModel):
    """郵便番号更新用モデル"""
    
    prefecture: Optional[str] = None
    city: Optional[str] = None
    town: Optional[str] = None
    weather_area_id: Optional[int] = None
    data_version: Optional[str] = None


class PostalCodeSearch(SQLModel):
    """郵便番号検索用モデル"""
    
    postal_code: Optional[str] = None
    prefecture: Optional[str] = None
    city: Optional[str] = None
    town: Optional[str] = None


class PostalCodeImportStats(SQLModel):
    """インポート統計情報"""
    
    total_processed: int
    created: int
    updated: int
    skipped: int
    errors: int
    data_version: str
    import_time: datetime


# 循環インポート回避のため、ここで WeatherAreaRead をインポート
from .weather_area import WeatherAreaRead
PostalCodeWithWeatherArea.model_rebuild()