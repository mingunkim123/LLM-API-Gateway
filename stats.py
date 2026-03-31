# stats.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from database import get_db
from models import RequestLog
from datetime import datetime, timedelta

router = APIRouter(prefix="/admin/stats", tags=["Statistics"])


@router.get("/summary")
async def get_summary(db: AsyncSession = Depends(get_db)):
    """핵심 KPI 요약 (전체 요청 수, 비용, 평균 지연시간)"""
    query = select(
        func.count(RequestLog.id).label("total_requests"),
        func.sum(RequestLog.estimated_cost).label("total_cost"),
        func.avg(RequestLog.latency_ms).label("avg_latency"),
    )
    result = await db.execute(query)
    summary = result.fetchone()

    return {
        "total_requests": summary.total_requests or 0,
        "total_cost": float(summary.total_cost or 0.0),
        "avg_latency_ms": float(summary.avg_latency or 0.0),
    }


@router.get("/usage/daily")
async def get_daily_usage(days: int = 7, db: AsyncSession = Depends(get_db)):
    """최근 N일간 일일 호출 수 트렌드"""
    since = datetime.now() - timedelta(days=days)

    # date_trunc는 PostgreSQL 함수입니다.
    query = (
        select(
            func.date_trunc("day", RequestLog.created_at).label("day"),
            func.count(RequestLog.id).label("count"),
        )
        .where(RequestLog.created_at >= since)
        .group_by("day")
        .order_by("day")
    )

    result = await db.execute(query)
    data = result.all()

    return [{"date": row.day.strftime("%Y-%m-%d"), "count": row.count} for row in data]


@router.get("/costs/by-tenant")
async def get_costs_by_tenant(db: AsyncSession = Depends(get_db)):
    """테넌트(팀)별 누적 비용 비중"""
    query = (
        select(
            RequestLog.tenant_name,
            func.sum(RequestLog.estimated_cost).label("total_cost"),
        )
        .group_by(RequestLog.tenant_name)
        .order_by(desc("total_cost"))
    )

    result = await db.execute(query)
    data = result.all()

    return [
        {"tenant": row.tenant_name, "cost": float(row.total_cost or 0.0)}
        for row in data
    ]


@router.get("/models/usage")
async def get_model_usage(db: AsyncSession = Depends(get_db)):
    """모델별 사용 빈도 비중"""
    query = (
        select(RequestLog.model_name, func.count(RequestLog.id).label("count"))
        .group_by(RequestLog.model_name)
        .order_by(desc("count"))
    )

    result = await db.execute(query)
    data = result.all()

    return [{"model": row.model_name, "count": row.count} for row in data]


@router.get("/logs/recent")
async def get_recent_logs(limit: int = 10, db: AsyncSession = Depends(get_db)):
    """최근 요청 로그 상세 (Last N)"""
    query = select(RequestLog).order_by(desc(RequestLog.created_at)).limit(limit)
    result = await db.execute(query)
    logs = result.scalars().all()

    return [
        {
            "id": log.id,
            "tenant": log.tenant_name,
            "model": log.model_name,
            "tokens": log.total_tokens,
            "cost": log.estimated_cost,
            "latency": log.latency_ms,
            "time": log.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for log in logs
    ]
