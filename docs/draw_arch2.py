from graphviz import Digraph

dot = Digraph("LLMGatewayArchitecture", format="png")
dot.attr(
    rankdir="TB", splines="ortho", nodesep="0.8", ranksep="0.7", fontname="sans-serif"
)
dot.attr(
    "node",
    shape="rect",
    style="rounded,filled",
    fontname="sans-serif",
    fontsize="14",
    height="0.6",
    penwidth="1.2",
)
dot.attr(
    "edge",
    fontname="sans-serif",
    fontsize="11",
    color="#555555",
    penwidth="1.2",
    arrowsize="0.8",
)

dot.attr(
    label="LLM API Gateway — Data Flow\n\n",
    fontsize="24",
    fontname="sans-serif",
    fontcolor="#333333",
)

# Color palette similar to user's example
C_APP = {"fillcolor": "#fa7a9b", "fontcolor": "black", "color": "#d74567"}  # Pink
C_ROUTE_P = {
    "fillcolor": "#f8d9df",
    "fontcolor": "#962d45",
    "color": "#f3aebf",
}  # Light Pink
C_ROUTE_G = {
    "fillcolor": "#d1ecf1",
    "fontcolor": "#0c5460",
    "color": "#bee5eb",
}  # Light Blue
C_HANDLERS = {"fillcolor": "#60a5fa", "fontcolor": "black", "color": "#2563eb"}  # Blue
C_MID = {"fillcolor": "#c084fc", "fontcolor": "black", "color": "#9333ea"}  # Purple
C_UTIL = {"fillcolor": "#cbd5e1", "fontcolor": "black", "color": "#94a3b8"}  # Grey
C_SER = {"fillcolor": "#fde047", "fontcolor": "black", "color": "#eab308"}  # Yellow
C_SVC = {"fillcolor": "#69f0ae", "fontcolor": "black", "color": "#00e676"}  # Mint Green
C_EXT = {"fillcolor": "#4b5563", "fontcolor": "white", "color": "#1f2937"}  # Dark Grey
C_DB1 = {
    "fillcolor": "#ffccbc",
    "fontcolor": "black",
    "color": "#f4511e",
}  # Light Orange
C_DB2 = {"fillcolor": "#ffab91", "fontcolor": "black", "color": "#e64a19"}  # Orange/Red
C_EXC = {"fillcolor": "#fca5a5", "fontcolor": "black", "color": "#ef4444"}  # Red

# 1. Apps
dot.node("Client", "📱 Client Apps", **C_APP, width="3.0")

# 2. Routes (Endpoints)
dot.node("R_Chat", "POST /api/v1/chat/", **C_ROUTE_P)
dot.node("R_Models", "GET /api/v1/models/", **C_ROUTE_G)

# 3. Handlers
dot.node("H_Chat", "chat.py", **C_HANDLERS)
dot.node("H_Models", "models.py", **C_HANDLERS)

# 4. Middlewares / Serializers
dot.node("Auth", "auth_middleware.py", **C_UTIL)
dot.node("RateLimiter", "rate_limiter.py", **C_SER)
dot.node("LLMClient", "llm_client.py", **C_MID)
dot.node("Logger", "logger.py", **C_UTIL)

# 5. Core Business Logic
dot.node(
    "ProxySvc",
    "LLMProxyService\nBusiness Logic",
    **C_SVC,
    width="3.0",
    height="1.0",
    fontsize="16",
)

# 6. Output / Ext
dot.node("PostgreSQL", "🐘 PostgreSQL", **C_DB1)
dot.node("Redis", "🔴 Redis", **C_DB2)
dot.node("LLM", "☁️ LLM API", **C_EXT)

# 7. Error
dot.node("Exceptions", "exceptions.py", **C_EXC, width="2.0")

# Flow Definitions
dot.edge("Client", "R_Chat")
dot.edge("Client", "R_Models")

dot.edge("R_Chat", "H_Chat")
dot.edge("R_Models", "H_Models")

# Request goes to Auth
dot.edge("H_Chat", "Auth")
dot.edge("H_Models", "Auth")

dot.edge("Auth", "RateLimiter")
dot.edge("RateLimiter", "ProxySvc")
dot.edge("ProxySvc", "LLMClient")

dot.edge("LLMClient", "LLM")

# Interactions with DBs
dot.edge("ProxySvc", "Redis", label=" Cache", color="#555555")
dot.edge("ProxySvc", "Logger", label=" Async")
dot.edge("Logger", "PostgreSQL", label=" Save", color="#555555")
dot.edge("Auth", "PostgreSQL", label=" Validate", color="#555555")
dot.edge("RateLimiter", "Redis", label=" Count", color="#555555")

# Exceptions Flow
dot.edge("H_Chat", "Exceptions", style="dashed", label=" Error")
dot.edge("Auth", "Exceptions", style="dashed", label=" Error")
dot.edge("ProxySvc", "Exceptions", style="dashed", label=" Error")

dot.render("/home/mingun/AI_Flatform/llm-gateway/docs/architecture_img", cleanup=True)
