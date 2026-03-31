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
