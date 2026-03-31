# dashboard/app.py
import streamlit as st
import pandas as pd
import httpx
import asyncio

from metrics import draw_cost_trend, draw_model_usage, draw_latency_dist

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

# 메인 UI
st.title("🚀 LLM API Gateway Monitor")
st.markdown(
    "전체 팀의 LLM 사용량, 비용 및 성능 지표를 실시간으로 확인합니다. (API 기반)"
)

# 데이터 로딩 실행
summary, df = asyncio.run(load_dashboard_data())

st.sidebar.title("🛠️ Control Panel")
demo_mode = st.sidebar.checkbox("Multi-Agent Offloading Demo", value=True)

if demo_mode:
    st.subheader("🤖 Multi-Agent Offloading Simulation")
    st.info(
        "복합 요청을 입력하면 시스템이 자원을 분석하여 Edge/Local/Cloud로 작업을 자동 배분합니다."
    )

    user_input = st.text_input(
        "Complex Prompt를 입력하세요:", value="데이터 분석하고 요약해서 메일로 보내줘"
    )

    if st.button("Offloading 실행"):

        async def run_demo():
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    "http://localhost:8005/v1/orchestrate", json={"prompt": user_input}
                )
                return res.json()

        result = asyncio.run(run_demo())

        if result:
            plan = result.get("offloading_plan", [])
            st.write(f"**총 {len(plan)}개의 에이전트 태스크가 생성되었습니다.**")

            # 테이블로 시각화
            plan_df = pd.DataFrame(plan)
            st.table(
                plan_df[["agent_type", "required_vram", "selected_model", "decision"]]
            )

            # 다이어그램 느낌의 시각화 (Expander 활용)
            cols = st.columns(len(plan))
            for i, p in enumerate(plan):
                with cols[i]:
                    st.success(f"Task: {p['agent_type']}")
                    st.metric("VRAM", f"{p['required_vram']}GB")
                    st.caption(f"📍 {p['selected_model']}")

st.divider()

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
