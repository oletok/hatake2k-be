from sqlmodel import SQLModel, Field, Relationship, Column
from typing import Optional, List
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB

from .crop import Crop
from .weather_area import WeatherArea


class CropWeatherArea(SQLModel, table=True):
    """作物×気象地域の栽培難易度"""
    __tablename__ = "crop_weather_areas"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    crop_id: int = Field(foreign_key="crops.id", index=True)
    weather_area_id: int = Field(foreign_key="weather_areas.id", index=True)
    difficulty: int = Field(description="露地栽培難易度 (1-100)")
    difficulty_reasons: List[str] = Field(default_factory=list, sa_column=Column(JSONB), description="難易度の理由配列")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # Relationships
    crop: Optional[Crop] = Relationship()
    weather_area: Optional[WeatherArea] = Relationship()
    
    def get_difficulty_reasons_list(self) -> List[str]:
        """難易度理由をリストで取得"""
        return self.difficulty_reasons or []
    
    class Config:
        # crop_id + weather_area_id の組み合わせをユニークにする
        table_args = (
            {"sqlite_autoincrement": True},
        )


class CropWeatherAreaCreate(SQLModel):
    crop_id: int
    weather_area_id: int
    difficulty: int
    difficulty_reasons: List[str] = []


class CropWeatherAreaRead(SQLModel):
    id: int
    crop_id: int
    weather_area_id: int
    difficulty: int
    difficulty_reasons: List[str]
    created_at: datetime
    updated_at: datetime
    crop: Optional[Crop] = None
    weather_area: Optional[WeatherArea] = None
    
    def get_difficulty_reasons_list(self) -> List[str]:
        """難易度理由をリストで取得"""
        return self.difficulty_reasons or []


class CropWeatherAreaUpdate(SQLModel):
    difficulty: Optional[int] = None
    difficulty_reasons: Optional[List[str]] = None