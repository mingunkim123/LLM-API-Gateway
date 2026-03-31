# proxy.py (Step 11: 스마트 정책 엔진 통합)
import httpx
from sqlalchemy import select
from database import AsyncSessionLocal
from models import LLMModel, Tenant
from policy import evaluate_policy


async def get_model_info(model_name: str) -> LLMModel | None:
    """DB에서 특정 모델 정보를 조회합니다."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(LLMModel).where(LLMModel.name == model_name))
        return result.scalar_one_or_none()


async def get_tenant_policy(tenant_name: str) -> str:
    """DB에서 테넌트(팀)의 라우팅 정책을 조회합니다."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Tenant).where(Tenant.name == tenant_name))
        tenant = result.scalar_one_or_none()
        return tenant.routing_policy if tenant else "cost_optimal"


async def get_all_active_models() -> list[LLMModel]:
    """DB에서 모든 활성 모델 리스트를 조회합니다."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(LLMModel).where(LLMModel.status.in_(["prod", "staging"]))
        )
        return list(result.scalars().all())


async def forward_to_llm(payload: dict, tenant_name: str) -> dict:
    # 1. 사용자가 특정 모델을 명시했는지 확인
    requested_model_name = payload.get("model")
    target_model = None

    if requested_model_name:
        # 특정 모델 요청 시, 해당 모델 정보 조회
        target_model = await get_model_info(requested_model_name)

    # 2. 모델 지정이 없거나, 지정된 모델이 없는 경우 '정책 엔진' 가동
    if not target_model:
        policy = await get_tenant_policy(tenant_name)
        all_models = await get_all_active_models()
        target_model = evaluate_policy(policy, all_models)

        if target_model:
            print(
                f"[Policy] 팀 '{tenant_name}' 정책({policy})에 따라 '{target_model.name}' 선정."
            )
        else:
            print("[Warning] 적절한 모델을 찾지 못했습니다. 기본 폴백 사용.")

    # 3. 최종 엔드포인트 결정
    target_url = (
        target_model.endpoint_url if target_model else "https://httpbin.org/post"
    )
    model_res_name = target_model.name if target_model else "fallback"

    # 4. 실제 요청 전달
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(target_url, json=payload, timeout=5.0)
            response.raise_for_status()
            res_json = response.json()

            # 응답에 실제 사용된 모델명을 명시 (중요: 정책 엔진이 골라준 경우 알 수 있게)
            if isinstance(res_json, dict):
                res_json["model"] = model_res_name
            return res_json

        except (httpx.TimeoutException, httpx.HTTPError) as e:
            print(f"[Error] 모델 호출 실패 ({target_url}): {e}")
            fallback_res = await client.post(
                "https://httpbin.org/post", json={"msg": "최종 비상 폴백 응답입니다."}
            )
            return fallback_res.json()
