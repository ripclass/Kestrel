import networkx as nx

from app.core.graph.analyzer import graph_metrics


def export_graph(
    graph: nx.DiGraph,
    focus_entity_id: str,
) -> dict[str, object]:
    nodes = [
        {
            "id": node_id,
            "type": data.get("type", "account"),
            "label": data.get("label", node_id),
            "subtitle": data.get("subtitle", ""),
            "risk_score": int(data.get("risk_score", 0)),
            "severity": data.get("severity", "low"),
        }
        for node_id, data in graph.nodes(data=True)
    ]
    edges = []
    for source, target, data in graph.edges(data=True):
        edges.append(
            {
                "id": data.get("id", f"{source}:{target}:{data.get('relation', 'edge')}"),
                "source": source,
                "target": target,
                "label": data.get("label", data.get("relation", "linked")),
                "relation": data.get("relation", "linked"),
                "amount": data.get("amount"),
            }
        )

    return {
        "focus_entity_id": focus_entity_id,
        "stats": graph_metrics(graph, focus_entity_id),
        "nodes": nodes,
        "edges": edges,
    }
