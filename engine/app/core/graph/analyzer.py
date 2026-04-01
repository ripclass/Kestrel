import networkx as nx

from app.core.graph.builder import build_graph


def graph_metrics() -> dict[str, int]:
    graph = build_graph()
    return {
        "node_count": graph.number_of_nodes(),
        "edge_count": graph.number_of_edges(),
        "communities": nx.number_weakly_connected_components(graph),
    }
