from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from sqlmodel import SQLModel, Field, Column, DateTime, Relationship
from pydantic import BaseModel

if TYPE_CHECKING:
    from .postal_code import PostalCode
    from .user import User


class WeatherAreaBase(SQLModel):
    """気象地域基本モデル"""
    prefecture: str = Field(index=True, description="都道府県名")
    region: str = Field(index=True, description="地方・区分")
    data_version: str = Field(description="データバージョン")


class WeatherArea(WeatherAreaBase, table=True):
    """気象地域テーブル"""
    __tablename__ = "weather_areas"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime, nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime, nullable=False, onupdate=datetime.now)
    )
    
    # リレーション
    postal_codes: List["PostalCode"] = Relationship(back_populates="weather_area")
    users: List["User"] = Relationship(back_populates="weather_area")


class WeatherAreaCreate(WeatherAreaBase):
    """気象地域作成用モデル"""
    pass


class WeatherAreaRead(WeatherAreaBase):
    """気象地域読み取り用モデル"""
    id: int
    created_at: datetime
    updated_at: datetime


class WeatherAreaSearch(BaseModel):
    """気象地域検索用モデル"""
    prefecture: Optional[str] = None
    region: Optional[str] = None


class WeatherAreaImportStats(BaseModel):
    """気象地域インポート統計"""
    total_processed: int
    created: int
    updated: int
    skipped: int
    errors: int
    data_version: str
    import_time: datetime