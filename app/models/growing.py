from sqlmodel import SQLModel, Field, Relationship, Column
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB

if TYPE_CHECKING:
    from .user import User
    from .crop import Crop


class Growing(SQLModel, table=True):
    """栽培テーブル（ユーザー×作物の関係）"""
    __tablename__ = "growings"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True, description="ユーザーID")
    crop_id: int = Field(foreign_key="crops.id", index=True, description="農作物ID")
    notes: List[str] = Field(default_factory=list, sa_column=Column(JSONB), description="栽培メモ・ノート")
    created_at: datetime = Field(default_factory=datetime.now, description="作成日時")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新日時")
    
    # リレーション
    user: Optional["User"] = Relationship(back_populates="growings")
    crop: Optional["Crop"] = Relationship(back_populates="growings")


class GrowingCreate(SQLModel):
    """栽培関係作成用モデル"""
    user_id: int
    crop_id: int
    notes: List[str] = []


class GrowingRead(SQLModel):
    """栽培関係読み取り用モデル"""
    id: int
    user_id: int
    crop_id: int
    notes: List[str]
    created_at: datetime
    updated_at: datetime


class GrowingWithDetails(SQLModel):
    """栽培関係（詳細情報含む）読み取り用モデル"""
    id: int
    user_id: int
    crop_id: int
    notes: List[str]
    created_at: datetime
    updated_at: datetime
    user: Optional["User"] = None
    crop: Optional["Crop"] = None