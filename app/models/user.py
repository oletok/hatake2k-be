from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlmodel import SQLModel, Field, Column, DateTime, Relationship

if TYPE_CHECKING:
    from .weather_area import WeatherArea


class UserBase(SQLModel):
    """ユーザー基本モデル"""
    firebase_uid: str = Field(unique=True, index=True, description="Firebase UID")
    email: str = Field(unique=True, index=True, description="メールアドレス")
    display_name: Optional[str] = Field(default=None, description="表示名")
    photo_url: Optional[str] = Field(default=None, description="プロフィール画像URL")
    bio: Optional[str] = Field(default=None, description="自己紹介")
    weather_area_id: Optional[int] = Field(default=None, foreign_key="weather_areas.id", description="気象地域ID")
    is_active: bool = Field(default=True, description="アカウント有効フラグ")


class User(UserBase, table=True):
    """ユーザーテーブル"""
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime, nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime, nullable=False, onupdate=datetime.now)
    )
    last_login_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime, nullable=True)
    )
    
    # リレーション
    weather_area: Optional["WeatherArea"] = Relationship(back_populates="users")


class UserCreate(UserBase):
    """ユーザー作成用モデル"""
    pass


class UserRead(UserBase):
    """ユーザー読み取り用モデル"""
    id: int
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime]


class UserUpdate(SQLModel):
    """ユーザー更新用モデル"""
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    bio: Optional[str] = None
    weather_area_id: Optional[int] = None
    is_active: Optional[bool] = None
    last_login_at: Optional[datetime] = None