from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from typing import List, Dict, Any, Optional

from ..models.user import User
from ..models.crop import Crop
from ..models.weather_area import WeatherArea
# from ..models.crop_weather_area import CropWeatherArea
from ..models.growing import Growing
from ..core.database import get_session
from ..core.logging import get_logger

router = APIRouter(prefix="/me", tags=["me"])
logger = get_logger("me_api")


def get_current_user_id() -> int:
    """現在のユーザーIDを取得（認証機能実装後に置き換え予定）"""
    # TODO: 認証機能実装後に JWT トークンからユーザーIDを取得するように変更
    return 1


@router.get("", response_model=Dict[str, Any])
def get_me(
    session: Session = Depends(get_session),
    current_user_id: int = Depends(get_current_user_id)
):
    """現在のユーザー情報を取得"""
    logger.info(f"ユーザー{current_user_id}の情報取得")
    
    # ユーザーを取得
    user = session.exec(select(User).where(User.id == current_user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    
    # 気象地域情報も含めて返却
    weather_area = None
    if user.weather_area_id:
        weather_area = session.exec(
            select(WeatherArea).where(WeatherArea.id == user.weather_area_id)
        ).first()
    
    return {
        "id": user.id,
        "firebase_uid": user.firebase_uid,
        "email": user.email,
        "display_name": user.display_name,
        "photo_url": user.photo_url,
        "bio": user.bio,
        "weather_area_id": user.weather_area_id,
        "weather_area": {
            "id": weather_area.id,
            "prefecture": weather_area.prefecture,
            "region": weather_area.region,
            "created_at": weather_area.created_at,
            "updated_at": weather_area.updated_at,
        } if weather_area else None,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "last_login_at": user.last_login_at
    }

@router.get("/growings", response_model=List[Dict[str, Any]])
def get_my_growings(
    session: Session = Depends(get_session),
    current_user_id: int = Depends(get_current_user_id)
):
    """ユーザーが栽培している作物一覧を取得"""
    logger.info(f"ユーザー{current_user_id}の栽培作物一覧取得")
    
    # ユーザーを取得
    user = session.exec(select(User).where(User.id == current_user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    
    # ユーザーの栽培作物を取得
    query = select(Growing, Crop).join(
        Crop, Growing.crop_id == Crop.id
    ).where(
        Growing.user_id == current_user_id
    ).order_by(Growing.created_at.desc())
    
    results = session.exec(query).all()
    
    growings = []
    for growing, crop in results:
        growings.append({
            "id": growing.id,
            "notes": growing.notes,
            "created_at": growing.created_at,
            "updated_at": growing.updated_at,
            "crop": {
                "id": crop.id,
                "code": crop.code,
                "name": crop.name,
                "category": crop.category,
                "aliases": crop.aliases,
                "difficulty": crop.difficulty,
                "difficulty_reasons": crop.difficulty_reasons,
                "created_at": crop.created_at,
                "updated_at": crop.updated_at,
            }
        })
    
    return growings

# @router.get("/crops/{crop_code}", response_model=Dict[str, Any])
# def get_my_crop_difficulty(
#     crop_code: str,
#     session: Session = Depends(get_session),
#     current_user_id: int = Depends(get_current_user_id)
# ):
#     """自分の気象地域での特定作物栽培難易度を取得"""
#     logger.info(f"ユーザー{current_user_id}の作物{crop_code}栽培難易度取得")
    
#     # ユーザーを取得
#     user = session.exec(select(User).where(User.id == current_user_id)).first()
#     if not user:
#         raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    
#     if not user.weather_area_id:
#         raise HTTPException(status_code=400, detail="気象地域が設定されていません")
    
#     # 作物を取得
#     crop = session.exec(select(Crop).where(Crop.code == crop_code)).first()
#     if not crop:
#         raise HTTPException(status_code=404, detail=f"作物コード '{crop_code}' が見つかりません")
    
#     # 気象地域情報を取得
#     weather_area = session.exec(
#         select(WeatherArea).where(WeatherArea.id == user.weather_area_id)
#     ).first()
    
#     # 作物×気象地域の難易度を取得
#     difficulty = session.exec(
#         select(CropWeatherArea).where(
#             CropWeatherArea.crop_id == crop.id,
#             CropWeatherArea.weather_area_id == user.weather_area_id
#         )
#     ).first()
    
#     if not difficulty:
#         raise HTTPException(
#             status_code=404, 
#             detail=f"この気象地域での作物 '{crop_code}' の栽培難易度データが見つかりません"
#         )
    
#     return {
#         "crop": {
#             "id": crop.id,
#             "code": crop.code,
#             "name": crop.name,
#             "category": crop.category,
#             "aliases": crop.aliases,
#             "difficulty": crop.difficulty,
#             "difficulty_reasons": crop.difficulty_reasons
#         },
#         "outdoor_cultivation": {
#             "difficulty": difficulty.difficulty,
#             "difficulty_reasons": difficulty.difficulty_reasons
#         },
#         "weather_area": {
#             "id": weather_area.id,
#             "prefecture": weather_area.prefecture,
#             "region": weather_area.region
#         },
#         "created_at": difficulty.created_at,
#         "updated_at": difficulty.updated_at
#     }