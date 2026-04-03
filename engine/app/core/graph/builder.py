from collections.abc import Sequence

import networkx as nx

from app.models.connection import Connection
from app.models.entity import Entity


def _edge_amount(connection: Connection) -> float | None:
    evidence = connection.evidence if isinstance(connection.evidence, dict) else {}
    for key in ("amount", "total_amount", "exposure"):
        value = evidence.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    return None


def build_graph(entities: Sequence[Entity], connections: Sequence[Connection]) -> nx.DiGraph:
    graph = nx.DiGraph()
    for entity in entities:
        graph.add_node(
            str(entity.id),
            type=entity.entity_type,
            label=entity.display_value,
            subtitle=entity.display_name or entity.entity_type.replace("_", " "),
            risk_score=entity.risk_score or 0,
            severity=entity.severity or "low",
        )

    for connection in connections:
        amount = _edge_amount(connection)
        graph.add_edge(
            str(connection.from_entity_id),
            str(connection.to_entity_id),
            id=str(connection.id),
            relation=connection.relation,
            amount=amount,
            label=f"BDT {amount:,.0f}" if isinstance(amount, (int, float)) else connection.relation.replace("_", " "),
        )

    return graph
