# auth.py (수정 — Step 6: DB 기반 인증)
from fastapi import Header, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from models import ApiKey
from rate_limit import check_rate_limit


async def verify_api_key(
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    # 1. DB에서 API Key 조회 (팀 정보도 함께 가져옴)
    result = await db.execute(
        select(ApiKey)
        .options(selectinload(ApiKey.tenant))
        .where(ApiKey.key == x_api_key, ApiKey.is_active == True)
    )
    api_key_row = result.scalar_one_or_none()

    # 2. 키가 없거나 비활성화 상태면 401
    if api_key_row is None:
        raise HTTPException(status_code=401, detail="Invalid API Key")

    # 3. Rate Limit 검증 (기존과 동일)
    check_rate_limit(x_api_key)

    # 4. 팀 이름을 반환 (기존에 딕셔너리에서 꺼내던 것과 동일한 역할)
    return api_key_row.tenant.name
