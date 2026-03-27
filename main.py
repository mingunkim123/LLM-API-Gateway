# main.py (수정)
import uvicorn
import time
from fastapi import FastAPI, Depends, Body, BackgroundTasks
from auth import verify_api_key
from proxy import forward_to_llm
from logger import save_log_data


app = FastAPI()


# /health는 누구나 들어와야 하므로 인증 없음
@app.get("/health")
async def health_check():
    return {"status": "ok"}


# 3. /v1/chat 라우터에 미들웨어(Depends) 부착
# 파라미터에 depends를 넣어두면, 이 함수가 실행되기 전 철저히 검사함
@app.post("/v1/chat")
async def secure_chat(
    background_tasks: BackgroundTasks,  # 추가됨!
    tenant_name: str = Depends(verify_api_key),
    payload: dict = Body(...),
):
    start_time = time.time()

    # 1. 프록시 돌리기 (도중에 에러 나면 알아서 Fallback탐)
    llm_result = await forward_to_llm(payload)

    # 2. 수행 시간 측정
    elapsed_time = time.time() - start_time

    # 3. 사용자에게 즉답하기 전에, 뒷정리 예약 (대기시간 0초)
    background_tasks.add_task(save_log_data, tenant_name, 200, elapsed_time)

    # 4. 사용자에겐 즉시 리턴
    return {"proxy_success": True, "llm_response": llm_result}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8005)
