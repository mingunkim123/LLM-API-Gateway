# main.py (수정)
import uvicorn
from fastapi import FastAPI, Depends
from auth import verify_api_key

app = FastAPI()


# /health는 누구나 들어와야 하므로 인증 없음
@app.get("/health")
async def health_check():
    return {"status": "ok"}


# 3. /v1/chat 라우터에 미들웨어(Depends) 부착
# 파라미터에 depends를 넣어두면, 이 함수가 실행되기 전 철저히 검사함
@app.post("/v1/chat")
async def secure_chat(tenant_name: str = Depends(verify_api_key)):
    return {"message": "인증 통과, API 호출 성공", "user_team": tenant_name}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8005)
