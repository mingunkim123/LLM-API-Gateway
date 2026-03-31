# proxy.py (Step 10: DB 기반 동적 라우팅)
import httpx
from sqlalchemy import select
from database import AsyncSessionLocal
from models import LLMModel


async def get_model_info(model_name: str) -> LLMModel | None:
    """DB에서 모델 정보를 조회합니다."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(LLMModel).where(LLMModel.name == model_name))
        return result.scalar_one_or_none()


async def forward_to_llm(payload: dict) -> dict:
    # 1. 사용자가 요청한 모델명 확인 (없으면 기본값 gpt-4o)
    requested_model = payload.get("model", "gpt-4o")

    # 2. DB(Model Registry)에서 해당 모델의 실제 엔드포인트 조회
    model_info = await get_model_info(requested_model)

    # 3. 만약 DB에 없거나 점검 중(dev)이면 폴백(Fallback) 처리
    if not model_info or model_info.status == "dev":
        print(
            f"[Info] 모델 '{requested_model}'이 레지스트리에 없거나 비활성 상태입니다. 기본 폴백 사용."
        )
        target_url = "https://httpbin.org/post"  # 임시 폴백
    else:
        target_url = model_info.endpoint_url
        print(
            f"[Routing] 모델 '{requested_model}' -> {target_url} 로 요청을 전달합니다."
        )

    # 4. 실제 요청 전달
    async with httpx.AsyncClient() as client:
        try:
            # 이제 하드코딩된 URL 대신 target_url을 사용함!
            response = await client.post(target_url, json=payload, timeout=5.0)
            response.raise_for_status()
            return response.json()

        except (httpx.TimeoutException, httpx.HTTPError) as e:
            print(f"[Error] 모델 호출 실패 ({target_url}): {e}")
            # 장애 발생 시 한 번 더 안전장치(Fallback)
            fallback_res = await client.post(
                "https://httpbin.org/post", json={"msg": "최종 비상 폴백 응답입니다."}
            )
            return fallback_res.json()
