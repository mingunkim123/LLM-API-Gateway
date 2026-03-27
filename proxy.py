# proxy.py
import httpx

# (테스트용) 들어온 요청을 그대로 리턴해주는 무료 메아리 API 서버
TARGET_LLM_URL = "https://httpbin.org/post"


async def forward_to_llm(payload: dict) -> dict:
    """외부 LLM API로 데이터를 무사히 넘기고 결과를 받아오는 함수"""
    # httpx를 써서 타겟 서버에 실제 HTTP POST 요청을 날림
    async with httpx.AsyncClient() as client:
        # LLM 응답이 오래 걸릴 수 있으니 timeout은 넉넉히 설정
        response = await client.post(TARGET_LLM_URL, json=payload, timeout=10.0)

        # 실제 받은 응답(상태코드와 데이터)을 파이썬 딕셔너리로 묶어 리턴
        return {"target_status": response.status_code, "target_data": response.json()}
