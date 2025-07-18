from sqlmodel import SQLModel, Field, Column
from typing import Optional, List
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB


class Crop(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(unique=True, index=True)
    category: str = Field(index=True)
    name: str = Field(index=True)
    aliases: List[str] = Field(default_factory=list, sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

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
    created_at: datetime
    updated_at: datetime

    def get_aliases_list(self) -> List[str]:
        """異名をリストで取得"""
        return self.aliases or []


class CropUpdate(SQLModel):
    category: Optional[str] = None
    name: Optional[str] = None
    aliases: Optional[List[str]] = None