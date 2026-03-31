# models.py
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class Tenant(Base):
    """팀(조직) 테이블 — 누가 우리 게이트웨이를 쓰는지 관리"""

    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)  # 예: "team-a"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # 기본 라우팅 정책: cost_optimal(비용), quality_first(성능), speed_optimal(속도)
    routing_policy: Mapped[str] = mapped_column(String(50), default="cost_optimal")

    # 한 팀이 여러 API Key를 발급받을 수 있음 (1:N 관계)
    api_keys: Mapped[list["ApiKey"]] = relationship(back_populates="tenant")


class ApiKey(Base):
    """API Key 테이블 — 하드코딩 딕셔너리를 DB로 옮긴 것"""

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(
        String(100), unique=True, index=True
    )  # 예: "sk-my-secret-key-1"
    is_active: Mapped[bool] = mapped_column(default=True)  # 키 비활성화 기능
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # 이 키가 어떤 팀 소속인지 (N:1 관계)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"))
    tenant: Mapped["Tenant"] = relationship(back_populates="api_keys")


class RequestLog(Base):
    """요청 로그 테이블 — 누가 언제 어떤 모델을 호출했고 얼마나 썼는지 기록"""

    __tablename__ = "request_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_name: Mapped[str] = mapped_column(String(100))  # 팀 이름
    model_name: Mapped[str] = mapped_column(
        String(100), default="unknown"
    )  # 사용된 모델명

    # 토큰 사용량 추적 (비용 정산의 핵심 데이터)
    prompt_tokens: Mapped[int] = mapped_column(default=0)  # 입력 토큰 수
    completion_tokens: Mapped[int] = mapped_column(default=0)  # 출력 토큰 수
    total_tokens: Mapped[int] = mapped_column(default=0)  # 총 토큰 수
    estimated_cost: Mapped[float] = mapped_column(default=0.0)  # 예상 비용 (USD)

    # 성능 지표
    latency_ms: Mapped[float] = mapped_column(default=0.0)  # 응답 지연시간 (ms)
    status_code: Mapped[int] = mapped_column(default=200)  # HTTP 상태 코드

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class LLMModel(Base):
    """모델 레지스트리 — 시스템에 등록된 모든 LLM 모델의 메타데이터 관리"""

    __tablename__ = "llm_models"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)  # 예: "gpt-4o"
    provider: Mapped[str] = mapped_column(String(50))  # 예: "openai", "anthropic"
    endpoint_url: Mapped[str] = mapped_column(String(255))
    api_key_env: Mapped[str] = mapped_column(
        String(100), nullable=True
    )  # 환경변수명 (선택)

    # 모델 상태: prod(운영), staging(검증), dev(개발/중지)
    status: Mapped[str] = mapped_column(String(20), default="dev")

    # 과금 모델 (1K 토큰당 가격)
    cost_per_1k_prompt: Mapped[float] = mapped_column(default=0.0)
    cost_per_1k_completion: Mapped[float] = mapped_column(default=0.0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
