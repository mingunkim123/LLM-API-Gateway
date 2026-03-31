# registry.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import LLMModel
from pydantic import BaseModel

router = APIRouter(prefix="/admin/models", tags=["Model Registry"])


# 데이터 검증용 스키마 (Pydantic)
class ModelCreate(BaseModel):
    name: str
    provider: str
    endpoint_url: str
    cost_per_1k_prompt: float = 0.0
    cost_per_1k_completion: float = 0.0


@router.get("")
async def list_models(db: AsyncSession = Depends(get_db)):
    """모든 등록된 모델 목록 조회"""
    result = await db.execute(select(LLMModel))
    return result.scalars().all()


@router.post("")
async def register_model(model_in: ModelCreate, db: AsyncSession = Depends(get_db)):
    """새로운 LLM 모델 등록"""
    new_model = LLMModel(**model_in.model_dump())
    db.add(new_model)
    await db.commit()
    await db.refresh(new_model)
    return new_model


@router.patch("/{model_id}/status")
async def update_model_status(
    model_id: int, status: str, db: AsyncSession = Depends(get_db)
):
    """모델 상태 변경 (dev -> staging -> prod)"""
    model = await db.get(LLMModel, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    model.status = status
    await db.commit()
    return {"message": f"Model {model.name} status updated to {status}"}
