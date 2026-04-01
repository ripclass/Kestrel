import networkx as nx

from app.core.graph.builder import build_graph


def shortest_path(source: str, target: str) -> list[str]:
    graph = build_graph()
    try:
        return nx.shortest_path(graph, source, target)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return []
