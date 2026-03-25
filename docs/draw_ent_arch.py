from graphviz import Digraph

dot = Digraph("EnterpriseArchitecture", format="png")
dot.attr(
    rankdir="TB", splines="ortho", nodesep="0.6", ranksep="0.6", fontname="sans-serif"
)
dot.attr(
    "node",
    shape="rect",
    style="rounded,filled",
    fontname="sans-serif",
    fontsize="13",
    height="0.6",
    penwidth="1.2",
)
dot.attr("edge", fontname="sans-serif", fontsize="11", color="#444444", penwidth="1.2")

dot.attr(
    label="Enterprise AI Platform Architecture\n\n", fontsize="24", fontcolor="#222222"
)

C_APP = {"fillcolor": "#fa7a9b", "fontcolor": "black", "color": "#d74567"}
C_GW = {"fillcolor": "#60a5fa", "fontcolor": "black", "color": "#2563eb"}
C_POLICY = {"fillcolor": "#fde047", "fontcolor": "black", "color": "#eab308"}
C_MLOPS = {"fillcolor": "#c084fc", "fontcolor": "white", "color": "#9333ea"}
C_OPS = {"fillcolor": "#69f0ae", "fontcolor": "black", "color": "#00e676"}
C_DB = {"fillcolor": "#ffccbc", "fontcolor": "black", "color": "#f4511e"}
C_REDIS = {"fillcolor": "#ffab91", "fontcolor": "black", "color": "#e64a19"}
C_LLM = {"fillcolor": "#4b5563", "fontcolor": "white", "color": "#1f2937"}

dot.node("Client", "👥 Tenants\n(Teams, Users)", **C_APP, width="2.5")

with dot.subgraph(name="cluster_Gateway") as c:
    c.attr(
        style="rounded,dashed",
        color="#aaaaaa",
        label="LLM API Gateway Layer",
        fontcolor="#555555",
    )
    c.node("Auth", "🛡️ Auth & Multi-tenancy\n(Quotas, API Keys)", **C_GW, width="2.5")
    c.node("RateLimit", "🚦 Traffic Control\n(Rate Limit, Cache)", **C_GW, width="2.5")
    c.node(
        "Policy",
        "🧠 Smart Policy Engine\n(Cost/Latency/Quality Routing)",
        **C_POLICY,
        width="3.0",
    )
    c.node(
        "Proxy",
        "🔁 Model Proxy Switcher\n(Load Balancing, Auto-Fallback)",
        **C_GW,
        width="3.0",
    )

with dot.subgraph(name="cluster_MLOps") as c:
    c.attr(
        style="rounded,dashed",
        color="#aaaaaa",
        label="MLOps Control Plane",
        fontcolor="#555555",
    )
    c.node(
        "Registry",
        "📦 Model Registry\n(Version, Staging/Prod Status)",
        **C_MLOPS,
        width="2.8",
    )
    c.node(
        "Eval", "⚙️ Auto-Eval Pipeline\n(Automated Benchmarks)", **C_MLOPS, width="2.8"
    )

with dot.subgraph(name="cluster_Ops") as c:
    c.attr(
        style="rounded,dashed",
        color="#aaaaaa",
        label="Operations & Monitoring",
        fontcolor="#555555",
    )
    c.node("Logger", "📝 Async Logger", **C_OPS, width="2.0")
    c.node(
        "Dashboard",
        "📊 Operations Dashboard\n(Cost, Usage, Latency)",
        **C_OPS,
        width="3.0",
    )

dot.node("PG", "🐘 PostgreSQL\n(Keys, Policies, Metrics)", **C_DB)
dot.node("Redis", "🔴 Redis\n(Cache/Limits)", **C_REDIS)

dot.node("LLMs", "🌥️ External Models\n(GPT, Claude)", **C_LLM, width="2.5")
dot.node("Local", "🖥️ Local Models\n(vLLM, Ollama)", **C_LLM, width="2.5")

dot.edge("Client", "Auth")
dot.edge("Auth", "RateLimit")
dot.edge("RateLimit", "Policy")
dot.edge("Policy", "Proxy")

dot.edge("Proxy", "LLMs", label=" Request")
dot.edge("Proxy", "Local")

dot.edge("Auth", "PG", style="dashed")
dot.edge("RateLimit", "Redis", style="dashed")
dot.edge("Proxy", "Logger", style="dashed")
dot.edge("Logger", "PG")

dot.edge("Registry", "Eval", label=" Trigger Eval")
dot.edge("Registry", "PG", style="dashed")
dot.edge("Eval", "Policy", label=" Configures Rules", style="dotted")
dot.edge("Dashboard", "PG", label=" Query Metrics", style="dotted")

dot.render(
    "/home/mingun/AI_Flatform/llm-gateway/docs/ent_architecture_img", cleanup=True
)
