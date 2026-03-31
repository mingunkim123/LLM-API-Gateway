# dashboard/metrics.py
import plotly.express as px
import pandas as pd


def draw_cost_trend(df: pd.DataFrame):
    """일자별 비용 트렌드 차트"""
    if df.empty:
        return None

    # 시간 데이터를 일자별로 그룹화
    df["date"] = df["time"].dt.date
    daily_cost = df.groupby("date")["cost"].sum().reset_index()

    fig = px.line(
        daily_cost,
        x="date",
        y="cost",
        title="💰 일일 누적 비용 트렌드",
        labels={"cost": "Cost ($)", "date": "Date"},
    )
    fig.update_traces(line_color="#FF4B4B")
    return fig


def draw_model_usage(df: pd.DataFrame):
    """모델별 사용 비중 (Donut Chart)"""
    if df.empty:
        return None

    model_counts = df["model"].value_counts().reset_index()
    model_counts.columns = ["model", "count"]

    fig = px.pie(
        model_counts,
        values="count",
        names="model",
        hole=0.4,
        title="🤖 모델별 요청 비중",
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    return fig


def draw_latency_dist(df: pd.DataFrame):
    """지연시간 분포 (Histogram)"""
    if df.empty:
        return None

    fig = px.histogram(
        df,
        x="latency",
        nbins=20,
        title="⚡ 지연시간 분포 (ms)",
        labels={"latency": "Latency (ms)"},
    )
    fig.update_traces(marker_color="#00CC96")
    return fig
