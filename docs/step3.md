# 3단계: 비동기 프록시 라우터 (외부 모델 중계하기)

## 지금 내가 하는 것(개념)
우리의 진짜 목적인 **리버스 프록시(Reverse Proxy)** 역할을 구현합니다.
게이트웨이 자체는 대답을 알지 못하므로, 클라이언트가 보내온 질문(바디)을 받아 그대로 **진짜 인공지능 서버(OpenAI 등)** 에 `POST` 요청을 비동기로 넘깁니다(Forward). 
곧이어 OpenAI가 답을 주면, 게이트웨이는 그걸 클라이언트에게 그대로 돌려줍니다. 사용자 입장에선 게이트웨이가 인공지능인 것처럼 보입니다.

## 생성할 파일
- `proxy.py`
- `main.py` (업데이트)

## 내가 직접 구현해야 할 내용(체크리스트)
- 환경 세팅: `pip install httpx` (파이썬 비동기 HTTP 통신 라이브러리)
- **`proxy.py`**
  - 가상의 OpenAI API 주소(혹은 무료 테스트용 API) 변수 선언
  - `forward_to_llm(payload: dict)` 비동기 함수 구현
  - `httpx.AsyncClient()`를 사용해 실제 타겟 URL로 `POST` 요청 보내기
  - 타겟 서버에서 돌아온 응답 상태 코드(status)와 JSON 결과를 그대로 반환
- **`main.py`**
  - Step 2에서 만든 `POST /v1/chat` 안에서 `forward_to_llm` 함수를 호출 대기(`await`)
  - 결과물을 `return`

## 여기서 중요한 HTTP 포인트(짧게 정리)
- **비동기 대기(Await)**: `httpx`로 요청을 날리고 응답이 오기까지 체감상 1~5초가 걸립니다. 이 동안 서버가 뻗지 않도록 반드시 `await` 키워드를 써야 합니다.
- **Client Session**: 매 요청마다 `httpx.AsyncClient()`를 생성하고 지우면(`async with`) 자원 정리가 깔끔합니다. (운영 환경에선 풀(Pool)을 사용하기도 함)

## 테스트(직접 확인)

**1. 서버 실행:**
```bash
python main.py
```

**2. 인증키와 함께 질문 던지기:**
(OpenAI API 연동 전이므로 `https://httpbin.org/post` 라는 더미 API를 타겟으로 삼아 중계를 테스트합니다.)
```bash
curl -X POST http://localhost:8000/v1/chat \
     -H "x-api-key: sk-my-secret-key-1" \
     -H "Content-Type: application/json" \
     -d '{"messages": [{"role": "user", "content": "안녕?"}]}'

# 기대: 
# 약간의 시간이 걸린 후, 우리가 보낸 JSON이 httpbin 서버를 거쳐 
# 되돌아온 결과(proxy_response)가 포함되어 200 OK로 떨어져야 함.
```

## 정답 코드(막히면 참고)

```python
# proxy.py
import httpx

# (테스트용) 들어온 요청을 그대로 리턴해주는 무료 메아리 API 서버
TARGET_LLM_URL = "https://httpbin.org/post"

async def forward_to_llm(payload: dict) -> dict:
    """외부 LLM API로 데이터를 무사히 넘기고 결과를 받아오는 함수"""
    # httpx를 써서 타겟 서버에 실제 HTTP POST 요청을 날림
    async with httpx.AsyncClient() as client:
        # LLM 응답이 오래 걸릴 수 있으니 timeout은 넉넉히 설정
        response = await client.post(
            TARGET_LLM_URL, 
            json=payload, 
            timeout=10.0
        )
        
        # 실제 받은 응답(상태코드와 데이터)을 파이썬 딕셔너리로 묶어 리턴
        return {
            "target_status": response.status_code,
            "target_data": response.json()
        }
```

```python
# main.py (수정)
import uvicorn
from fastapi import FastAPI, Depends, Body
from auth import verify_api_key
from proxy import forward_to_llm

app = FastAPI()

@app.post("/v1/chat")
# 파라미터로 헤더 인증(Depends)과 바디 전체(Body)를 동시에 받음
async def secure_chat(
    tenant_name: str = Depends(verify_api_key),
    payload: dict = Body(...)
):
    print(f"[{tenant_name}] 사용자가 프록시 요청을 보냈습니다.")
    
    # 1. proxy.py의 포워딩 함수를 비동기로 호출하고 멍때리며(?) 기다림
    result = await forward_to_llm(payload)
    
    # 2. 밖에서 받아온 결과를 클라이언트에게 그대로 토스
    return {
        "proxy_success": True,
        "caller": tenant_name,
        "llm_response": result["target_data"]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```
