# logger.py (수정 — Step 7: DB 기반 로깅)
from database import AsyncSessionLocal
from models import RequestLog


async def save_log_data(
    tenant: str,
    status: int,
    latency: float,
    model_name: str = "unknown",
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    estimated_cost: float = 0.0,
):
    """응답을 이미 돌려준 후 뒤에서 DB에 로그를 저장하는 함수"""
    total_tokens = prompt_tokens + completion_tokens

    async with AsyncSessionLocal() as session:
        log = RequestLog(
            tenant_name=tenant,
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost=estimated_cost,
            latency_ms=latency * 1000,  # 초 → 밀리초 변환
            status_code=status,
        )
        session.add(log)
        await session.commit()

    print(
        f"\n[DB Log] 팀 '{tenant}' | 모델: {model_name} | "
        f"토큰: {total_tokens} | 비용: ${estimated_cost:.4f} | "
        f"지연: {latency * 1000:.0f}ms"
    )
