from pydantic import BaseModel
from typing import List


class AgentTask(BaseModel):
    task_id: str
    agent_type: str  # 'analyser', 'summarizer', 'mailer'
    description: str
    priority: int = 1
    # 요구되는 문맥 복잡도 (토큰 수)
    expected_tokens: int = 1000
    # 최종 계산된 VRAM (프로파일러가 채움)
    req_vram_gb: float = 0.0
    req_latency_sec: float = 0.0


class OrchestratedRequest(BaseModel):
    original_prompt: str
    sub_tasks: List[AgentTask]


async def decompose_task(prompt: str) -> OrchestratedRequest:
    """
    사용자의 복합 요청을 에이전트별 하위 작업으로 분해합니다.
    실무에서는 LLM(예: GPT-4)을 호출하여 JSON 형태로 분해하지만,
    여기서는 개념 증명을 위해 규칙 기반으로 분해 로직을 시뮬레이션합니다.
    """
    # 시뮬레이션: 프롬프트에 특정 키워드가 있으면 태스크 추가
    tasks = []

    if "분석" in prompt or "analyze" in prompt.lower():
        tasks.append(
            AgentTask(
                task_id="task_1_analysis",
                agent_type="analyser",
                description="데이터 패턴 분석 및 통계 추출",
                expected_tokens=4096,  # 분석은 긴 문맥 필요
                req_latency_sec=5.0,
            )
        )

    if "요약" in prompt or "summarize" in prompt.lower():
        tasks.append(
            AgentTask(
                task_id="task_2_summary",
                agent_type="summarizer",
                description="분석 결과 요약",
                expected_tokens=1024,  # 요약은 상대적으로 적은 VRAM 필요
                req_latency_sec=2.0,
            )
        )

    if "메일" in prompt or "email" in prompt.lower():
        tasks.append(
            AgentTask(
                task_id="task_3_mail",
                agent_type="mailer",
                description="결과 보고서 메일 발송",
                expected_tokens=256,  # 메일은 연산 거의 없음 (Edge 가능)
                req_latency_sec=1.0,
            )
        )

    # 만약 아무 키워드도 없다면 기본 챗봇 태스크로 할당
    if not tasks:
        tasks.append(
            AgentTask(
                task_id="task_default",
                agent_type="chatbot",
                description="일반 대화 응답",
                expected_tokens=512,
                req_latency_sec=1.5,
            )
        )

    return OrchestratedRequest(original_prompt=prompt, sub_tasks=tasks)


class ModelConfig(BaseModel):
    name: str
    params_b: float  # Billion parameters (7B, 175B 등)
    precision_bit: int  # 4-bit, 8-bit, 16-bit
    kv_cache_factor: float  # 토큰당 KV 캐시 점유율 (MB/token)


# 시뮬레이션을 위한 데이터베이스 (실무에선 DB에서 가져옴)
MODEL_SPECS = {
    "gpt-4o": ModelConfig(
        name="gpt-4o", params_b=30.0, precision_bit=16, kv_cache_factor=0.5
    ),  # Cloud급 (30B)
    "cheap-gpt": ModelConfig(
        name="cheap-gpt", params_b=7.0, precision_bit=4, kv_cache_factor=0.1
    ),  # Local급 (7B)
    "premium-gpt": ModelConfig(
        name="premium-gpt", params_b=2.0, precision_bit=4, kv_cache_factor=0.05
    ),  # Edge급 (2B)
}


def estimate_resource_usage(task: AgentTask, model_name: str) -> AgentTask:
    """
    [전기전자 전공 Deep Dive: 하드웨어 프로파일링 심화]
    모델의 파라미터 수, 퀀타이즈(Quantization) 비트 수, 문맥 길이를 기반으로
    필요한 VRAM(GB)을 반환합니다.

    공식: VRAM_GB = (Params_B * (Bit / 8)) + (Context_Length * KV_Cache_Factor / 1024)
    """
    spec = MODEL_SPECS.get(model_name)
    if not spec:
        return task

    # 1. Weights 메모리 점유량 (모델 가중치 로드용)
    weights_vram = spec.params_b * (spec.precision_bit / 8.0)

    # 2. KV Cache 메모리 점유량 (문맥 처리를 위한 가동 메모리)
    kv_cache_vram = (task.expected_tokens * spec.kv_cache_factor) / 1024.0

    total_required = weights_vram + kv_cache_vram

    # 태스크 정보 업데이트
    task.req_vram_gb = round(total_required, 2)
    task.description += (
        f" (예측된 VRAM: {task.req_vram_gb}GB, {spec.precision_bit}-bit 기준)"
    )

    return task
