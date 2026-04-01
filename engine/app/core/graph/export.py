from seed.fixtures import GRAPH


def export_graph() -> dict[str, object]:
    return GRAPH.model_dump()
