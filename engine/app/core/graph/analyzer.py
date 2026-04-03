import networkx as nx

def graph_metrics(graph: nx.DiGraph, focus_entity_id: str) -> dict[str, int]:
    if focus_entity_id in graph:
        lengths = nx.single_source_shortest_path_length(graph.to_undirected(), focus_entity_id, cutoff=3)
    else:
        lengths = {}

    return {
        "node_count": graph.number_of_nodes(),
        "edge_count": graph.number_of_edges(),
        "max_depth": max(lengths.values(), default=0),
        "suspicious_paths": sum(
            1
            for node_id, depth in lengths.items()
            if depth > 0 and int(graph.nodes[node_id].get("risk_score", 0)) >= 70
        ),
    }
