import networkx as nx

from seed.fixtures import GRAPH


def build_graph() -> nx.DiGraph:
    graph = nx.DiGraph()
    for node in GRAPH.nodes:
        graph.add_node(node.id, **node.model_dump())
    for edge in GRAPH.edges:
        graph.add_edge(edge.source, edge.target, **edge.model_dump())
    return graph
