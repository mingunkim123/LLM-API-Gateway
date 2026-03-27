# auth.py
from fastapi import Header, HTTPException
from rate_limit import check_rate_limit

# 1. DB를 대체할 임시 키 리스트
VALID_API_KEYS = {"sk-my-secret-key-1": "team-a", "sk-my-secret-key-2": "team-b"}


# 2. 문지기(Dependency) 함수


async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API Key")

    # 🔑 인증을 통과하자마자(올바른 사용자임) 무조건 Rate Limit을 검증한다!
    # 여기서 Exception이 발생하면 라우터까지 안가고 바로 차단됨
    check_rate_limit(x_api_key)

    return VALID_API_KEYS[x_api_key]
