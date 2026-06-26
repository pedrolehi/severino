from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from rag.subgraph import nodes
from rag.subgraph.state import RagSubgraphState


def build_rag_subgraph():
    workflow = StateGraph(RagSubgraphState)

    workflow.add_node("prepare_query", nodes.prepare_query)
    workflow.add_node("retrieve", nodes.retrieve)
    workflow.add_node("retrieval_gate", nodes.retrieval_gate)
    workflow.add_node("build_context", nodes.build_context)
    workflow.add_node("generate", nodes.generate)
    workflow.add_node("judge", nodes.judge)
    workflow.add_node("rewrite_query", nodes.rewrite_query)
    workflow.add_node("pack_response", nodes.pack_response)
    workflow.add_node("mark_fallback", nodes.mark_fallback)

    workflow.add_edge(START, "prepare_query")
    workflow.add_edge("prepare_query", "retrieve")
    workflow.add_edge("retrieve", "retrieval_gate")
    workflow.add_conditional_edges(
        "retrieval_gate",
        nodes.route_after_retrieval_gate_node,
        {
            "build_context": "build_context",
            "rewrite_query": "rewrite_query",
            "end_fallback": "mark_fallback",
        },
    )
    workflow.add_edge("rewrite_query", "retrieve")
    workflow.add_edge("build_context", "generate")
    workflow.add_edge("generate", "judge")
    workflow.add_conditional_edges(
        "judge",
        lambda state: (
            "pack_response"
            if (state.get("judge_verdict") or {}).get("action") == "accept"
            else (
                "rewrite_query"
                if (state.get("judge_verdict") or {}).get("action") == "retry_search"
                else "mark_fallback"
            )
        ),
        {
            "pack_response": "pack_response",
            "rewrite_query": "rewrite_query",
            "mark_fallback": "mark_fallback",
        },
    )
    workflow.add_edge("pack_response", END)
    workflow.add_edge("mark_fallback", END)

    return workflow.compile()
