# proxy.py (수정)
import httpx

TARGET_LLM_URL = "https://httpbin.org/delay/5"  # 고의로 5초 지연시키는 API
FALLBACK_LLM_URL = "https://httpbin.org/post"


async def forward_to_llm(payload: dict) -> dict:
    async with httpx.AsyncClient() as client:
        try:
            # 타임아웃 1초로 공격 (무조건 에러 터짐)
            response = await client.post(TARGET_LLM_URL, json=payload, timeout=1.0)
            response.raise_for_status()  # 400~500번대 에러면 파이썬 에러 던짐
            return response.json()

        except (httpx.TimeoutException, httpx.HTTPError) as e:
            print(f"[Warning] 본진 서버 장애 발생! 원인: {e}. Fallback 가동합니다.")

            # 여기서 다른 싼 모델이나 로컬 모델로 우회시킴
            fallback_res = await client.post(
                FALLBACK_LLM_URL, json={"msg": "이건 백업 모델 로직입니다"}
            )
            return fallback_res.json()
