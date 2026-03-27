# main.py (수정)
import uvicorn
from fastapi import FastAPI, Depends, Body
from auth import verify_api_key
from proxy import forward_to_llm

app = FastAPI()


# /health는 누구나 들어와야 하므로 인증 없음
@app.get("/health")
async def health_check():
    return {"status": "ok"}


# 3. /v1/chat 라우터에 미들웨어(Depends) 부착
# 파라미터에 depends를 넣어두면, 이 함수가 실행되기 전 철저히 검사함
@app.post("/v1/chat")
# 파라미터로 헤더 인증(Depends)과 바디 전체(Body)를 동시에 받음
async def secure_chat(
    tenant_name: str = Depends(verify_api_key), payload: dict = Body(...)
):
    print(f"[{tenant_name}] 사용자가 프록시 요청을 보냈습니다.")

    # 1. proxy.py의 포워딩 함수를 비동기로 호출하고 멍때리며(?) 기다림
    result = await forward_to_llm(payload)

    # 2. 밖에서 받아온 결과를 클라이언트에게 그대로 토스
    return {
        "proxy_success": True,
        "caller": tenant_name,
        "llm_response": result["target_data"],
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8005)
