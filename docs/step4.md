# 4단계: 트래픽 제어 (Redis 기반 Rate Limiting)

## 지금 내가 하는 것(개념)
나쁜 의도든 버그든, 한 클라이언트가 초당 100개씩 API를 쏘면 외부 LLM 비용 한도가 터지게 됩니다.
이를 막기 위해 **초고속 인메모리 DB인 Redis**를 연동합니다. 누가 언제 API를 호출하면, Redis 안에 `key: sk-my-secret-key-1`, `value: 1`을 저장합니다. 이후 한 번 호출할 때마다 `Value`를 `+1` 시킵니다. 만약 값이 `5`를 넘으면 매몰차게 요청을 차단(`429 Error`)하는 로직입니다.

## 생성할 파일
- `docker-compose.yml` (Redis 실행용)
- `rate_limit.py`
- `main.py` (업데이트)

## 내가 직접 구현해야 할 내용(체크리스트)
- 의존성 설치: `pip install redis`
- **`docker-compose.yml`**: 로컬에 `redis:alpine` 이미지 띄우기 세팅
- 터미널에서 `docker-compose up -d` 명령어 실행
- **`rate_limit.py`**
  - `redis.Redis` 인스턴스 연결 (localhost:6379)
  - `check_rate_limit(api_key: str)` 검사 함수 작성
  - Redis의 `incr` (증가) 명령어와 `expire`(만료-예:60초) 설정 로직 추가
  - 카운트가 한계(예: 분당 3회)를 넘으면 `HTTPException(status_code=429)` 던지기
- **`auth.py` (수정)**
  - 인증 통과 직후 `check_rate_limit()` 함수를 호출하도록 로직 끼워넣기

## 여기서 중요한 HTTP 포인트(짧게 정리)
- **Status Code 429 (Too Many Requests)**: 서버는 안 죽었지만 "네가 너무 많이 보내서 조금 쉴게" 하고 튕겨내는 전용 상태 코드입니다.
- **TTL (Time To Live)**: Redis 데이터가 영원히 남아있으면 안 되므로, 카운터를 '60초' 마다 초기화(삭제)시킵니다. 분당 제한 로직의 핵심입니다.

## 테스트(직접 확인)

**1. Redis 인프라와 서버 실행:**
```bash
docker-compose up -d
python main.py
```

**2. 짧은 시간 내 여러 번 요청 달리기:**
1~3번째는 성공합니다. 하지만 4번째 요청부터 차단되어야 합니다.
```bash
# 터미널에서 빠르게 위 화살표 누르고 엔터 여러번 치기
curl -X POST http://localhost:8000/v1/chat -H "x-api-key: sk-my-secret-key-1" -H "Content-Type: application/json" -d "{}"

# 1~3번째 기대: {"proxy_success": true, ...} (200 OK)
# 4번째 기대: {"detail":"Too Many Requests"} (429 에러)
```
60초를 기다린 후 다시 쏘면 성공합니다!

## 정답 코드(막히면 참고)

```yaml
# docker-compose.yml
version: '3.8'
services:
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
```

```python
# rate_limit.py
import redis
from fastapi import HTTPException

# Redis 서버와 통신하는 뼈대 객체 파기
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

MAX_REQUESTS_PER_MINUTE = 3

def check_rate_limit(api_key: str):
    """API Key별로 분당 호출 횟수를 검사하는 함수"""
    redis_key = f"rate_limit:{api_key}"
    
    # 카운트 1 증가시킴 (키가 없으면 1로 자동 생성)
    current_count = r.incr(redis_key)
    
    # 처음 만들어진 키라면 60초 후에 자동 소멸되도록 폭탄 해제 시간 설정
    if current_count == 1:
        r.expire(redis_key, 60)
        
    # 만약 카운트가 한도를 넘었다면?
    if current_count > MAX_REQUESTS_PER_MINUTE:
        raise HTTPException(status_code=429, detail="Too Many Requests. 1분 뒤에 다시 시도하세요.")
```

```python
# auth.py (수정)
from fastapi import Header, HTTPException
from rate_limit import check_rate_limit

VALID_API_KEYS = {
    "sk-my-secret-key-1": "team-a",
    "sk-my-secret-key-2": "team-b"
}

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    # 🔑 인증을 통과하자마자(올바른 사용자임) 무조건 Rate Limit을 검증한다!
    # 여기서 Exception이 발생하면 라우터까지 안가고 바로 차단됨
    check_rate_limit(x_api_key)
    
    return VALID_API_KEYS[x_api_key]
```
