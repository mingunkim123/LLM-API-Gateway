# 2단계: 미들웨어를 이용한 보안 (API Key 인증)

## 지금 내가 하는 것(개념)
아무나 내 서버(그리고 비싼 LLM API)를 호출하지 못하도록 입구에 **검문소(문지기)**를 만듭니다.
클라이언트가 보내는 요청의 HTTP 헤더에 담긴 비밀번호(`Authorization: Bearer <Key>` 또는 `x-api-key`)를 매번 검사해야 합니다.
FastAPI의 **의존성 주입(Dependency Injection, `Depends`)** 기능을 사용하면, 라우터별로 똑같은 인증 코드를 복사/붙여넣기 할 필요 없이 공통으로 검문소를 강제해둘 수 있습니다.

## 생성할 파일
- `auth.py`
- `main.py` (업데이트)

## 내가 직접 구현해야 할 내용(체크리스트)
- **`auth.py`**
  - 가상의 유효한 API 키 목록(하드코딩 리스트) 생성 (예: `["sk-my-secret-key-1", "sk-my-secret-key-2"]`)
  - 검문소 역할을 할 `verify_api_key` 비동기 함수 만들기
  - 매개변수로 `x_api_key: str = Header(...)` 를 받아 헤더 값 추출
  - 추출한 키가 목록에 없다면 `HTTPException(status_code=401, detail="Invalid API Key")` 강제 발생
  - 일치하면 정상적으로 키 값을 리턴
- **`main.py`**
  - `auth.py`에서 함수를 가져와, 보안이 필요한 라우터(예: 새로 만들 `POST /v1/chat`)에 `Depends(verify_api_key)` 주입하기

## 여기서 중요한 HTTP 포인트(짧게 정리)
- **Header 추출**: URL 경로나 바디가 아닌, 메타데이터인 헤더(Headers)에서 비밀 키를 꺼내 읽습니다.
- **Status Code 401 (Unauthorized)**: "너는 인증되지 않은 사용자야"라고 내쫓을 때 사용하는 표준 HTTP 상태 코드입니다.
- **Depends**: FastAPI의 최대 장점. 코드가 실행되기 전(프리플라이트) 먼저 특정 함수를 실행시키고 통과해야만 본 라우터가 실행되게 만드는 마법입니다.

## 테스트(직접 확인)

**1. 서버 실행:**
```bash
python main.py
```

**2. 헤더 없이 혹은 틀린 키로 요청:**
```bash
curl -X POST http://localhost:8000/v1/chat
# 기대: {"detail":"Field required"} (422 에러, 헤더가 아예 없어서 막힘)

curl -X POST http://localhost:8000/v1/chat -H "x-api-key: invalid-key"
# 기대: {"detail":"Invalid API Key"} (401 Unauthorized 에러)
```

**3. 올바른 키로 요청:**
```bash
curl -X POST http://localhost:8000/v1/chat -H "x-api-key: sk-my-secret-key-1"
# 기대: {"message":"인증 통과, API 호출 성공"} (200 OK)
```

## 정답 코드(막히면 참고)

```python
# auth.py
from fastapi import Header, HTTPException

# 1. DB를 대체할 임시 키 리스트
VALID_API_KEYS = {
    "sk-my-secret-key-1": "team-a",
    "sk-my-secret-key-2": "team-b"
}

# 2. 문지기(Dependency) 함수
async def verify_api_key(x_api_key: str = Header(...)):
    # 헤더로 들어온 값이 유효한 키인지 확인
    if x_api_key not in VALID_API_KEYS:
        # 키가 없으면 401 에러 발생(즉시 응답 종료)
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    # 누군지(팀 이름) 리턴해주면 나중에 쓰기 편함
    return VALID_API_KEYS[x_api_key]
```

```python
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
    return {
        "message": "인증 통과, API 호출 성공",
        "user_team": tenant_name
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```
