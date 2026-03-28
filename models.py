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
