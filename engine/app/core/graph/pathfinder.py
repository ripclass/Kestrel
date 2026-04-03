import networkx as nx

def shortest_path(graph: nx.DiGraph, source: str, target: str) -> list[str]:
    try:
        return nx.shortest_path(graph, source, target)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return []
