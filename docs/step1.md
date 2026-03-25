# 1단계: FastAPI 기본 서버 띄우기 (+ GET /health)

## 지금 내가 하는 것(개념)
Python 표준 라이브러리(`http.server`)를 넘어, **초고속 비동기 처리에 특화된 최신 웹 프레임워크인 FastAPI**를 이용해 게이트웨이 서버의 뼈대를 만듭니다. 
현대적인 API 서버는 아래와 같이 동작합니다.
- `FastAPI()` 객체를 생성하여 웹 애플리케이션의 본체를 만듭니다.
- `@app.get("/health")` 와 같은 데코레이터를 이용해 "어떤 URL로, 어떤 요청(GET/POST)이 올 때 어느 함수를 실행할지" 연결(라우팅)합니다.
- 코드를 비동기(`async def`)로 작성하여, 트래픽이 몰려도 막힘(Blocking) 없이 처리하도록 구성합니다.
- `uvicorn`이라는 ASGI 엔진이 이 FastAPI 앱을 구동하여 실제 TCP 포트(8000)에서 대기시킵니다.

## 생성할 파일
- `main.py`
- `requirements.txt` (명령어로 설치)

## 내가 직접 구현해야 할 내용(체크리스트)
- 의존성 설치하기(`pip install fastapi uvicorn`)
- `FastAPI`, `uvicorn` 라이브러리 import
- `app = FastAPI()` 초기화
- `GET /health` 라우터 구현
  - `{"status": "ok"}` JSON 반환
- `POST /test` 라우터 구현 (간단한 바디 받기)
  - 파라미터로 `dict` 타입 바디 데이터를 받아 `{"message": "hello", "your_data": ...}` 형태로 반환
- `if __name__ == "__main__":` 블록에서 `uvicorn.run(app, host="0.0.0.0", port=8000)`으로 서버 실행

## 여기서 중요한 HTTP 포인트(짧게 정리)
- **ASGI 엔진 (Uvicorn)**: 파이썬에서 비동기 웹 통신을 처리하게 해주는 규격입니다.
- **라우팅 (Routing)**: `GET`, `POST` 등의 HTTP 메서드와 URL 경로(`/health`)에 따라 파이썬 함수를 매핑합니다.
- **자동 JSON 변환**: FastAPI는 파이썬 딕셔너리(`dict`)를 반환하면 귀찮게 `.encode()`를 하지 않아도 알아서 `application/json`으로 직렬화해줍니다.

## 테스트(직접 확인)

**1. 서버 실행:**
```bash
python main.py
```

**2. 다른 터미널에서 확인:**
```bash
curl http://localhost:8000/health
# 기대: {"status":"ok"} (200 OK)

curl http://localhost:8000/anything
# 기대: {"detail":"Not Found"} (404 Not Found - FastAPI가 자동 제공)

curl -X POST http://localhost:8000/test -H "Content-Type: application/json" -d '{"name":"AI"}'
# 기대: {"message":"hello","your_data":{"name":"AI"}} (200 OK)
```

## 정답 코드(막히면 참고)

```python
# main.py
import uvicorn
from fastapi import FastAPI
from typing import Dict, Any

# 1. FastAPI 애플리케이션 객체 생성
app = FastAPI(title="LLM API Gateway")

# 2. GET /health 구현
@app.get("/health")
async def health_check():
    # FastAPI는 파이썬 딕셔너리를 자동으로 JSON 응답(200 OK)으로 변환해줍니다.
    return {"status": "ok"}

# 3. POST /test 구현 (데이터를 받아서 그대로 돌려주는 에코 테스트)
@app.post("/test")
async def test_post(payload: Dict[str, Any]):
    return {
        "message": "hello",
        "your_data": payload
    }

# 4. 서버 구동
if __name__ == "__main__":
    print("Server running on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
```
