# main.py (수정 — Step 7: 토큰 정보 로깅)
import uvicorn
import time
from fastapi import FastAPI, Depends, Body, BackgroundTasks
from auth import verify_api_key
from proxy import forward_to_llm
from logger import save_log_data
from cache import get_cached_response, set_cached_response
from registry import router as model_registry_router
from stats import router as stats_router

app = FastAPI()

# 0. 관리자용 라우터 연결
app.include_router(model_registry_router)
app.include_router(stats_router)


# /health는 누구나 들어와야 하므로 인증 없음
@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/v1/chat")
async def secure_chat(
    background_tasks: BackgroundTasks,
    tenant_name: str = Depends(verify_api_key),
    payload: dict = Body(...),
):
    start_time = time.time()

    # 0. Redis 캐시 확인 (Cache Hit)
    cached_response = get_cached_response(payload)
    if cached_response:
        elapsed_time = time.time() - start_time
        # 캐시 히트라도 로그는 남깁니다 (디버깅/통계 목적) - 비용/토큰 사용량은 0!
        background_tasks.add_task(
            save_log_data,
            tenant=tenant_name,
            status=200,
            latency=elapsed_time,
            model_name="redis-cache-hit",
            prompt_tokens=0,
            completion_tokens=0,
            estimated_cost=0.0,
        )
        return {"proxy_success": True, "llm_response": cached_response, "cached": True}

    # 1. 캐시 미스(Miss) 시, 실제 프록시 요청 (도중에 에러 나면 알아서 Fallback탐)
    llm_result = await forward_to_llm(payload, tenant_name)

    # 1.5. 새로 받아온 응답을 빠른 서빙을 위해 캐시에 저장 (Write)
    set_cached_response(payload, llm_result)

    # 2. 수행 시간 측정
    elapsed_time = time.time() - start_time

    # 3. LLM 응답에서 토큰 사용량 파싱 (OpenAI 응답 포맷 기준)
    usage = llm_result.get("usage", {})
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    model_name = llm_result.get("model", "unknown")

    # 4. 간이 비용 계산 (GPT-4 기준 예시: 입력 $0.03/1K, 출력 $0.06/1K)
    estimated_cost = (prompt_tokens * 0.03 + completion_tokens * 0.06) / 1000

    # 5. 백그라운드로 DB에 로그 저장 예약
    background_tasks.add_task(
        save_log_data,
        tenant=tenant_name,
        status=200,
        latency=elapsed_time,
        model_name=model_name,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        estimated_cost=estimated_cost,
    )

    # 6. 사용자에겐 즉시 리턴
    return {"proxy_success": True, "llm_response": llm_result, "cached": False}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8005)
