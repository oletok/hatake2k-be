from sqlmodel import SQLModel, Field, Column, Relationship
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB

if TYPE_CHECKING:
    from .growing import Growing


class Crop(SQLModel, table=True):
    __tablename__ = "crops"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(unique=True, index=True)
    category: str = Field(index=True)
    name: str = Field(index=True)
    aliases: List[str] = Field(default_factory=list, sa_column=Column(JSONB))
    difficulty: Optional[int] = Field(default=None, description="栽培難易度 (1-100)")
    difficulty_reasons: List[str] = Field(default_factory=list, sa_column=Column(JSONB), description="難易度の理由配列")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # リレーション
    growings: List["Growing"] = Relationship(back_populates="crop")

    def get_aliases_list(self) -> List[str]:
        """異名をリストで取得"""
        return self.aliases or []

    def __repr__(self):
        return f"<Crop(code='{self.code}', name='{self.name}')>"


class CropCreate(SQLModel):
    code: str
    category: str
    name: str
    aliases: List[str] = []


class CropRead(SQLModel):
    id: int
    code: str
    category: str
    name: str
    aliases: List[str]
    difficulty: Optional[int]
    difficulty_reasons: List[str]
    created_at: datetime
    updated_at: datetime

    def get_aliases_list(self) -> List[str]:
        """異名をリストで取得"""
        return self.aliases or []


class CropUpdate(SQLModel):
    category: Optional[str] = None
    name: Optional[str] = None
    aliases: Optional[List[str]] = None
    difficulty: Optional[int] = None
    difficulty_reasons: Optional[List[str]] = None