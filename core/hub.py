from langgraph.graph.state import CompiledStateGraph
from graph.builder import build_graph


_graph_cache: dict[str, CompiledStateGraph] = {}


def build_thread_id(assistant_id, session_id) -> str:
    return f"{assistant_id}:{session_id}"


def get_graph(assistant_id: str) -> CompiledStateGraph:
    if assistant_id not in _graph_cache:
        _graph_cache[assistant_id] = build_graph(assistant_id)
    return _graph_cache[assistant_id]
