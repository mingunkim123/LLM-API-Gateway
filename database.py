# database.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

# PostgreSQL 접속 정보 (docker-compose.yml과 일치)
DATABASE_URL = "postgresql+asyncpg://gateway:gateway1234@localhost:5432/llm_gateway"

# 1. 비동기 엔진 생성 — DB와의 커넥션 풀(Pool)을 관리하는 핵심 객체
engine = create_async_engine(DATABASE_URL, echo=True)

# 2. 세션 팩토리 — 요청마다 독립적인 DB 세션(트랜잭션 단위)을 찍어내는 공장
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


# 3. ORM 모델의 부모 클래스 (models.py에서 이걸 상속받아 테이블을 정의함)
class Base(DeclarativeBase):
    pass


# 4. FastAPI의 Depends에 꽂을 세션 제공 함수
#    요청이 들어오면 세션을 열고, 처리가 끝나면 자동으로 닫아줌
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
