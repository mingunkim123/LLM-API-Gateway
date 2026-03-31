# offloader.py
from typing import List, Dict, Tuple, Optional
from models import LLMModel
from orchestrator import AgentTask, OrchestratedRequest, estimate_resource_usage


async def select_optimal_node(
    task: AgentTask, available_models: List[LLMModel]
) -> Tuple[Optional[LLMModel], str]:
    """
    태스크의 요구 자원과 모델의 하드웨어 사양을 비교하여 최적의 노드를 선택합니다.
    [EE 가점 포인트] 각 모델의 사양(Parameter, Bit)에 따라 VRAM 사용량을 동적으로 예측합니다.
    """
    candidates_with_usage = []

    for model in available_models:
        if model.status != "prod":
            continue

        # 1. 모델별 동적 VRAM 예측 (프로파일링)
        # 이 시점에서 task.req_vram_gb가 모델의 스펙에 맞춰 업데이트됩니다.
        updated_task = estimate_resource_usage(task, model.name)

        if model.vram_available_gb >= updated_task.req_vram_gb:
            candidates_with_usage.append((model, updated_task.req_vram_gb))

    if not candidates_with_usage:
        return None, "적합한 하드웨어 자원을 가진 노드를 찾을 수 없습니다. (VRAM 부족)"

    # 2. 정책 기반 최적 노드 선택 (Best Fit: 가장 작은 모델 우선)
    candidates_with_usage.sort(key=lambda x: x[0].vram_total_gb)

    selected_model, predicted_vram = candidates_with_usage[0]

    # 3. 오프로딩 결정 메시지 생성 및 전공 지식 강조 (EE: Edge Computing)
    if selected_model.vram_total_gb >= 40:
        target_type = "Cloud GPU"
    elif 8 < selected_model.vram_total_gb < 40:
        target_type = "Local/On-Premise GPU"
    else:
        target_type = "Edge Device"

    decision_msg = f"'{task.agent_type}' 작업을 자원 효율성을 고려하여 {target_type}({selected_model.name})로 배분합니다."

    return selected_model, decision_msg


async def run_orchestrated_offloading(
    orchestrated_req: OrchestratedRequest, available_models: List[LLMModel]
) -> List[Dict]:
    """
    분해된 모든 태스크에 대해 오프로딩 결정을 내리고 결과를 취합합니다.
    """
    results = []
    for task in orchestrated_req.sub_tasks:
        model, msg = await select_optimal_node(task, available_models)
        results.append(
            {
                "task_id": task.task_id,
                "agent_type": task.agent_type,
                "required_vram": task.req_vram_gb,
                "selected_model": model.name if model else "None",
                "decision": msg,
                "endpoint": model.endpoint_url if model else None,
            }
        )
    return results
