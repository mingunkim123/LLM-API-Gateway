# policy.py (Step 11: 스마트 정책 엔진)
from typing import List
from models import LLMModel


def evaluate_policy(policy_name: str, models: List[LLMModel]) -> LLMModel | None:
    """
    팀의 정책(policy_name)에 따라 가용 모델 리스트 중 최적의 모델을 선정합니다.
    """
    if not models:
        return None

    # 오직 운영 중(prod)이거나 검증 중(staging)인 모델만 대상 (dev는 배제)
    active_models = [m for m in models if m.status in ["prod", "staging"]]
    if not active_models:
        return None

    # 1. 비용 최적화 정책: 토큰당 단가가 가장 낮은 모델 선택
    if policy_name == "cost_optimal":
        return min(active_models, key=lambda x: x.cost_per_1k_prompt)

    # 2. 품질 우선 정책: 특정 프로바이더(OpenAI, Anthropic)나 특정 모델 우선
    elif policy_name == "quality_first":
        # 여기서는 단순히 OpenAI 모델을 우선순위에 둡니다. (추후 벤치마크 점수 컬럼 추가 가능)
        premium_providers = ["openai", "anthropic"]
        for provider in premium_providers:
            for m in active_models:
                if m.provider == provider:
                    return m
        return active_models[0]

    # 3. 속도 우선 정책 (현재는 기본값으로 처리)
    elif policy_name == "speed_optimal":
        return active_models[0]

    # 기본값: 리스트의 첫 번째 활성 모델 반환
    return active_models[0]
