# src/ai_job_agent/apps/graph/pipeline.py
from typing import TypedDict, Optional, Dict, Any
from langgraph.graph import StateGraph, START, END
from ai_job_agent.apps.llm.chains import compose_email

class EmailState(TypedDict, total=False):
    profile: Dict[str, Any]
    job: Dict[str, Any]
    contact: Optional[Dict[str, Any]]
    subject: str
    body: str

def prepare_context(state: EmailState) -> EmailState:
    # No heavy work here; just ensures keys exist
    state.setdefault("contact", None)
    return state

def generate_email(state: EmailState) -> EmailState:
    subject, body = compose_email(state["profile"], state["job"], state.get("contact"))
    state["subject"] = subject
    state["body"] = body
    return state

def format_output(state: EmailState) -> EmailState:
    # Could add post-processing (sign-off, limits) here
    return state

# Build the graph
graph = StateGraph(EmailState)
graph.add_node("prepare_context", prepare_context)
graph.add_node("generate_email", generate_email)
graph.add_node("format_output", format_output)

graph.add_edge(START, "prepare_context")
graph.add_edge("prepare_context", "generate_email")
graph.add_edge("generate_email", "format_output")
graph.add_edge("format_output", END)

email_graph = graph.compile()
