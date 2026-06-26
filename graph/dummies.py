"""Compat: nós legados removidos — use graph.rag_node e agents.fallback_agent."""

from agents.fallback_agent import fallback_agent
from graph.rag_node import rag_subgraph_node as rag_agent

__all__ = ["fallback_agent", "rag_agent"]
