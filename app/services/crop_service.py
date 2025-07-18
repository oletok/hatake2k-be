from typing import List, Optional
from sqlmodel import Session, select, func
from fastapi import HTTPException

from ..models.crop import Crop, CropCreate, CropRead
from ..core.logging import get_logger

logger = get_logger("crop_service")


class CropService:
    """作物サービス"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_crops(
        self,
        skip: int = 0,
        limit: int = 100,
        category: Optional[str] = None
    ) -> List[Crop]:
        """作物一覧を取得"""
        try:
            statement = select(Crop)
            
            if category:
                statement = statement.where(Crop.category == category)
            
            statement = statement.offset(skip).limit(limit)
            crops = self.session.exec(statement).all()
            
            logger.info(f"作物 {len(crops)} 件を取得しました")
            return crops
        
        except Exception as e:
            logger.error(f"作物一覧取得エラー: {e}")
            raise HTTPException(status_code=500, detail="作物一覧の取得に失敗しました")
    
    def get_crop_by_code(self, code: str) -> Crop:
        """作物コードで作物を取得"""
        try:
            statement = select(Crop).where(Crop.code == code)
            crop = self.session.exec(statement).first()
            
            if not crop:
                logger.warning(f"作物コード '{code}' が見つかりません")
                raise HTTPException(
                    status_code=404, 
                    detail=f"作物コード '{code}' が見つかりません"
                )
            
            logger.info(f"作物 '{crop.name}' を取得しました")
            return crop
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"作物取得エラー: {e}")
            raise HTTPException(status_code=500, detail="作物の取得に失敗しました")
    
    def search_crops(self, query: str, limit: int = 50) -> List[Crop]:
        """作物名・異名で検索"""
        try:
            # JSONB配列内での検索を行う（@> 演算子を使用）
            statement = select(Crop).where(
                (Crop.name.ilike(f"%{query}%")) | 
                (Crop.aliases.op('?|')(f'{{"{query}"}}')))
            
            # よりシンプルな検索に変更
            crops = self.session.exec(statement).all()
            
            # Python側でのフィルタリングも追加
            filtered_crops = []
            for crop in crops:
                # 名前での一致
                if query.lower() in crop.name.lower():
                    filtered_crops.append(crop)
                    continue
                
                # 異名での一致
                if crop.aliases:
                    for alias in crop.aliases:
                        if query.lower() in alias.lower():
                            filtered_crops.append(crop)
                            break
            
            # 重複を削除
            seen = set()
            result = []
            for crop in filtered_crops:
                if crop.id not in seen:
                    seen.add(crop.id)
                    result.append(crop)
            
            # 件数制限
            result = result[:limit]
            
            logger.info(f"'{query}' の検索結果: {len(result)} 件")
            return result
        
        except Exception as e:
            logger.error(f"作物検索エラー: {e}")
            raise HTTPException(status_code=500, detail="作物の検索に失敗しました")
    
    def get_categories(self) -> List[str]:
        """作物カテゴリー一覧を取得"""
        try:
            statement = select(Crop.category).distinct()
            categories = self.session.exec(statement).all()
            
            logger.info(f"カテゴリー {len(categories)} 件を取得しました")
            return sorted(categories)
        
        except Exception as e:
            logger.error(f"カテゴリー取得エラー: {e}")
            raise HTTPException(status_code=500, detail="カテゴリーの取得に失敗しました")
    
    def create_crop(self, crop_data: CropCreate) -> Crop:
        """作物を作成"""
        try:
            # 既存チェック
            existing = self.session.exec(
                select(Crop).where(Crop.code == crop_data.code)
            ).first()
            
            if existing:
                logger.warning(f"作物コード '{crop_data.code}' は既に存在します")
                raise HTTPException(
                    status_code=400, 
                    detail=f"作物コード '{crop_data.code}' は既に存在します"
                )
            
            crop = Crop(**crop_data.model_dump())
            self.session.add(crop)
            self.session.commit()
            self.session.refresh(crop)
            
            logger.info(f"作物 '{crop.name}' を作成しました")
            return crop
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"作物作成エラー: {e}")
            self.session.rollback()
            raise HTTPException(status_code=500, detail="作物の作成に失敗しました")
    
    def get_crop_count(self) -> int:
        """作物の総数を取得"""
        try:
            count = len(self.session.exec(select(Crop)).all())
            logger.info(f"作物総数: {count}")
            return count
        
        except Exception as e:
            logger.error(f"作物数取得エラー: {e}")
            raise HTTPException(status_code=500, detail="作物数の取得に失敗しました")