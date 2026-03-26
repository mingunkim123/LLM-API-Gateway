# auth.py
from fastapi import Header, HTTPException

# 1. DB를 대체할 임시 키 리스트
VALID_API_KEYS = {"sk-my-secret-key-1": "team-a", "sk-my-secret-key-2": "team-b"}


# 2. 문지기(Dependency) 함수
async def verify_api_key(x_api_key: str = Header(...)):
    # 헤더로 들어온 값이 유효한 키인지 확인
    if x_api_key not in VALID_API_KEYS:
        # 키가 없으면 401 에러 발생(즉시 응답 종료)
        raise HTTPException(status_code=401, detail="Invalid API Key")

    # 누군지(팀 이름) 리턴해주면 나중에 쓰기 편함
    return VALID_API_KEYS[x_api_key]
