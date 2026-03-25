from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.client import Users
from diagrams.programming.framework import Fastapi
from diagrams.onprem.inmemory import Redis
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.compute import Server

with Diagram("LLM API Gateway Architecture", show=False, filename="/home/mingun/AI_Flatform/llm-gateway/docs/architecture_img", direction="LR"):
    users = Users("Client App")
    llm = Server("External LLMs\n(OpenAI, Anthropic)")

    with Cluster("LLM Gateway (Docker Compose)"):
        gateway = Fastapi("FastAPI Gateway\n(Proxy, Auth)")
        cache = Redis("Redis\n(Rate Limit, Cache)")
        db = PostgreSQL("PostgreSQL\n(API Keys, Logs)")
        
        gateway >> Edge(label="Check Auth") >> db
        gateway >> Edge(label="Rate Limit/Cache") >> cache
        gateway >> Edge(style="dashed", color="gray", label="Async Log") >> db

    users >> Edge(color="blue", label="1. Request") >> gateway
    gateway >> Edge(color="darkgreen", label="2. Proxy Request") >> llm
    llm >> Edge(color="darkgreen", label="3. Response") >> gateway
    gateway >> Edge(color="blue", label="4. Return") >> users
