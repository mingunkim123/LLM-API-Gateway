from graphviz import Digraph

dot = Digraph("MLOpsWorkflow", format="png")
dot.attr(
    rankdir="LR", splines="ortho", nodesep="0.5", ranksep="0.6", fontname="sans-serif"
)
dot.attr(
    "node",
    shape="rect",
    style="rounded,filled",
    fontname="sans-serif",
    fontsize="12",
    height="0.5",
    penwidth="1.2",
)
dot.attr("edge", fontname="sans-serif", fontsize="10", color="#555555", penwidth="1.2")

dot.attr(
    label="Model Promotion & Evaluation Workflow (MLOps)\n\n",
    fontsize="24",
    fontcolor="#333333",
)

C_STEP = {"fillcolor": "#e0f2fe", "fontcolor": "#0369a1", "color": "#0ea5e9"}
C_TEST = {"fillcolor": "#fef08a", "fontcolor": "#854d0e", "color": "#eab308"}
C_DECISION = {
    "shape": "diamond",
    "fillcolor": "#fbcfe8",
    "fontcolor": "#9d174d",
    "color": "#ec4899",
    "style": "filled",
    "fixedsize": "false",
    "margin": "0.1",
}
C_PROD = {"fillcolor": "#bbf7d0", "fontcolor": "#166534", "color": "#22c55e"}
C_FAIL = {"fillcolor": "#fca5a5", "fontcolor": "#991b1b", "color": "#ef4444"}

dot.node("Dev", "1. Register Model\n(Version: v2.0-dev)", **C_STEP)
dot.node("Eval", "2. Auto-Eval Pipeline\n(Run Benchmarks)", **C_TEST)
dot.node("Compare", "Is v2.0 > Prod?", **C_DECISION)
dot.node("Reject", "Reject & Notify", **C_FAIL)
dot.node("Staging", "3. Promote to Staging\n(Shadow / A/B Target)", **C_STEP)
dot.node("Monitor", "4. Operations Monitor\n(Check Latency/Errors)", **C_TEST)
dot.node("Promote", "5. Promote to Prod\nPrimary Routing", **C_PROD)
dot.node("Rollback", "Auto-Rollback\n(If Failure Spike)", **C_FAIL)

dot.edge("Dev", "Eval")
dot.edge("Eval", "Compare")
dot.edge("Compare", "Reject", label=" No")
dot.edge("Compare", "Staging", label=" Yes")
dot.edge("Staging", "Monitor", label=" Shadow Traffic")
dot.edge("Monitor", "Promote", label=" Stable & Fast")
dot.edge("Monitor", "Rollback", label=" Errors Detected")
dot.edge("Promote", "Rollback", label=" Post-release Alert", style="dashed")
dot.edge("Rollback", "Staging", style="dashed")

dot.render("/home/mingun/AI_Flatform/llm-gateway/docs/ent_workflow_img", cleanup=True)
