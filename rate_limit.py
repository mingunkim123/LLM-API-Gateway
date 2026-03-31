# rate_limit.py
import redis
from fastapi import HTTPException

# Redis 서버와 통신하는 뼈대 객체 파기
r = redis.Redis(host="localhost", port=16379, db=0, decode_responses=True)

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
        raise HTTPException(
            status_code=429, detail="Too Many Requests. 1분 뒤에 다시 시도하세요."
        )
