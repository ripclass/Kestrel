from pydantic import BaseModel


class GraphNode(BaseModel):
    id: str
    type: str
    label: str
    subtitle: str
    risk_score: int
    severity: str


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str
    relation: str
    amount: float | None = None


class NetworkGraph(BaseModel):
    focus_entity_id: str
    stats: dict[str, int]
    nodes: list[GraphNode]
    edges: list[GraphEdge]
