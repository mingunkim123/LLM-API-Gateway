# dashboard/app.py
import streamlit as st
import pandas as pd
import httpx
import asyncio

# API 서버 주소 (main.py가 8005 포트에서 실행 중이면 맞춰야 함)
API_BASE_URL = "http://localhost:8005/admin/stats"

st.set_page_config(page_title="LLM Gateway Dashboard", layout="wide")


# API 호출을 위한 비동기 헬퍼 함수
async def fetch_api_data(endpoint: str):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_BASE_URL}{endpoint}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"API 연결 오류 ({endpoint}): {e}")
            return None


# 데이터 로드 로직 (API 기반)
async def load_dashboard_data():
    # 병렬로 API 호출
    summary_task = fetch_api_data("/summary")
    logs_task = fetch_api_data("/logs/recent")
    # 아래는 시각화용 데이터인데, metrics.py를 조금 수정해야 할 수도 있음
    # 일단은 logs 데이터로 데이터프레임을 만듭니다.

    summary, logs = await asyncio.gather(summary_task, logs_task)

    if summary and logs:
        df = pd.DataFrame(logs)
        # 시간 컬럼을 datetime으로 변환 (Plotly 등에서 사용)
        if not df.empty:
            df["time"] = pd.to_datetime(df["time"])
        return summary, df
    return None, None


# 시각화 함수 (metrics.py는 여전히 DataFrame을 받도록 유지)
from metrics import draw_cost_trend, draw_model_usage, draw_latency_dist

# 메인 UI
st.title("🚀 LLM API Gateway Monitor")
st.markdown(
    "전체 팀의 LLM 사용량, 비용 및 성능 지표를 실시간으로 확인합니다. (API 기반)"
)

# 데이터 로딩 실행
summary, df = asyncio.run(load_dashboard_data())

if summary is not None and df is not None:
    # 상단 요약 지표 (KPI Cards)
    col1, col2, col3 = st.columns(3)
    col1.metric("전체 요청 수", f"{summary['total_requests']} 건")
    col2.metric("누적 예상 비용", f"${summary['total_cost']:.4f}")
    col3.metric("평균 지연시간", f"{summary['avg_latency_ms']:.0f} ms")

    st.divider()

    # 시각화 차트
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(draw_cost_trend(df), use_container_width=True)
    with c2:
        st.plotly_chart(draw_model_usage(df), use_container_width=True)

    st.plotly_chart(draw_latency_dist(df), use_container_width=True)

    st.divider()

    # 상세 로그
    st.subheader("📋 최근 요청 로그")
    st.dataframe(df, use_container_width=True)
else:
    st.warning(
        "데이터를 불러올 수 없습니다. API 서버(main.py)가 실행 중인지 확인하세요."
    )

if st.button("새로고침"):
    st.rerun()
