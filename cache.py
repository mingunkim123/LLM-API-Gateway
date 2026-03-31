# cache.py
import json
import hashlib
from rate_limit import r  # 이미 만들어둔 Redis 연결(pool)을 재사용

# 캐시 만료 시간: 1시간(3600초)
CACHE_TTL = 3600


def get_cache_key(payload: dict) -> str:
    """사용자의 요청(payload)을 바탕으로 교유한 해시 키를 생성합니다."""
    # 1. 딕셔너리를 문자열로 변환 (순서가 달라도 동일하게 해싱되도록 sort_keys=True)
    payload_str = json.dumps(payload, sort_keys=True)

    # 2. 문자열을 SHA-256 해시로 변환하여 길이를 짧고 균일하게 만듦
    payload_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

    return f"llm_cache:{payload_hash}"


def get_cached_response(payload: dict) -> dict | None:
    """Redis에서 해시 키를 이용해 캐시된 응답을 찾습니다."""
    key = get_cache_key(payload)
    cached_data = r.get(key)

    if cached_data:
        # Redis 특성상 bytes 형태로 반환되므로 JSON(dict)으로 다시 복원
        return json.loads(cached_data)
    return None


def set_cached_response(payload: dict, response: dict):
    """LLM에서 받은 새 응답을 Redis에 저장합니다."""
    key = get_cache_key(payload)

    # setex: Set + Expire (저장과 동시에 타이머 설정)
    r.setex(key, CACHE_TTL, json.dumps(response))
