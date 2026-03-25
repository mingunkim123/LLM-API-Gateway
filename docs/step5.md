# 5단계: 백그라운드 로깅 및 Fallback (장애 복구)

## 지금 내가 하는 것(개념)
나중에 비용 정산 대시보드를 만들기 위해 '누가 언제 호출했고 몇 분이 걸렸다'는 **기록(로그)을 파일이나 DB에 몰래(비동기로) 적어둡니다.** 
또한 OpenAI API 서버가 갑자기 죽어 타임아웃이 났을 때, 사용자에게 에러를 뱉는 대신 "대안 모델" 로 즉시 우회(Fallback)호출하여 **운영 장애를 무마시키는 고가용성 패턴**을 짭니다.

## 생성할 파일
- `logger.py`
- `proxy.py` (업데이트)
- `main.py` (업데이트)

## 내가 직접 구현해야 할 내용(체크리스트)
- **`logger.py`**
  - 파라미터로 여러 정보를 받아 단순히 콘솔에 `[Log]` 글자와 저장하는 함수 작성
  - (나중에는 이곳에 실제로 Postgres `INSERT` 쿼리를 작성하면 완성됩니다.)
- **`main.py` (수정)**
  - 라우터 파라미터에 `background_tasks: BackgroundTasks` 추가 넣기
  - 응답 `return` 바로 윗줄에 `background_tasks.add_task(...)` 로 로깅 함수 예약 던지기
- **`proxy.py` (수정)**
  - `httpx.post()` 부분을 `try-except` 블록으로 감싸기
  - `httpx.TimeoutException, httpx.HTTPStatusError` 에러 시, `FALLBACK_URL` 로 한 번 더 `post()` 해보고 그 응답을 구출해서 반환하기

## 여기서 중요한 HTTP 포인트(짧게 정리)
- **Background Tasks**: HTTP 응답 코드가 다이렉트로 사용자에게 반환된 직후, 서버가 자기 혼자 남아있는 찌꺼기 작업(로깅)을 처리하게 해주는 FastAPI의 꿀 기능입니다.
- **예외 처리 (try-except)와 Fallback**: 네트워크 세계에서 남의 API는 무조건 믿으면 안 됩니다. 타임아웃 에러를 핸들링해서 대안망으로 우회하는 것이 플랫폼 엔지니어의 핵심 역할입니다.

## 테스트(직접 확인)

**1. 서버 실행:**
```bash
python main.py
```

**2. 에러 유발 및 우회 확인:**
코드의 `TARGET_LLM_URL`을 고의로 이상한 주소(`http://example.invalid`)로 바꾸거나 timeout을 0.001로 고장내보세요.
```bash
curl -X POST http://localhost:8000/v1/chat -H "x-api-key: sk-my-secret-key-1" -H "Content-Type: application/json" -d "{}"

# 기대 (정상인 척): {"proxy_success": true, "llm_response": "폴백 모델에서 대신 대답합니다!"...} (200 OK)
# 서버 터미널 로그에는 "[Log] 비동기로 기록을 저장했습니다" 메시지가 떠야합니다.
```

## 정답 코드(막히면 참고)

```python
# logger.py
import time
import asyncio

async def save_log_data(tenant: str, status: int, latency: float):
    """응답을 이미 돌려준 후 뒤에서 몰래 DB에 적는 척 하는 함수"""
    # 실제로는 이 부분에 비동기 DB Insert 코드가 들어갑니다.
    await asyncio.sleep(1) # 무거운 저장 작업 시뮬레이션
    print(f"\n[Background Log] 팀 '{tenant}' - 상태:{status} - 걸린시간:{latency:.2f}초 기록 완료!")
```

```python
# proxy.py (수정)
import httpx

TARGET_LLM_URL = "https://httpbin.org/delay/5" # 고의로 5초 지연시키는 API
FALLBACK_LLM_URL = "https://httpbin.org/post"

async def forward_to_llm(payload: dict) -> dict:
    async with httpx.AsyncClient() as client:
        try:
            # 타임아웃 1초로 공격 (무조건 에러 터짐)
            response = await client.post(TARGET_LLM_URL, json=payload, timeout=1.0)
            response.raise_for_status() # 400~500번대 에러면 파이썬 에러 던짐
            return response.json()
            
        except (httpx.TimeoutException, httpx.HTTPError) as e:
            print(f"[Warning] 본진 서버 장애 발생! 원인: {e}. Fallback 가동합니다.")
            
            # 여기서 다른 싼 모델이나 로컬 모델로 우회시킴
            fallback_res = await client.post(FALLBACK_LLM_URL, json={"msg": "이건 백업 모델 로직입니다"})
            return fallback_res.json()
```

```python
# main.py (수정)
import uvicorn
import time
from fastapi import FastAPI, Depends, Body, BackgroundTasks
from auth import verify_api_key
from proxy import forward_to_llm
from logger import save_log_data

app = FastAPI()

@app.post("/v1/chat")
async def secure_chat(
    background_tasks: BackgroundTasks, # 추가됨!
    tenant_name: str = Depends(verify_api_key),
    payload: dict = Body(...)
):
    start_time = time.time()
    
    # 1. 프록시 돌리기 (도중에 에러 나면 알아서 Fallback탐)
    llm_result = await forward_to_llm(payload)
    
    # 2. 수행 시간 측정
    elapsed_time = time.time() - start_time
    
    # 3. 사용자에게 즉답하기 전에, 뒷정리 예약 (대기시간 0초)
    background_tasks.add_task(save_log_data, tenant_name, 200, elapsed_time)
    
    # 4. 사용자에겐 즉시 리턴
    return {
        "proxy_success": True,
        "llm_response": llm_result
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```
