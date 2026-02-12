from visualization.graph_analytics import ForensicGraphAnalyzer
import networkx as nx

analyzer = ForensicGraphAnalyzer(db_path='forensic_data.db')
G = analyzer.build_communication_graph('sample_case_001', min_interactions=1)

print(f"Graph nodes: {G.number_of_nodes()}")
if G.number_of_nodes() > 0:
    first_node = list(G.nodes())[0]
    print(f"First node: {first_node}")
    print(f"Node attributes: {G.nodes[first_node]}")
    
    # Check if any node has a real name
    named_nodes = [n for n, d in G.nodes(data=True) if d.get('name') and d.get('name') != 'Unknown']
    print(f"Nodes with names: {len(named_nodes)}")
    if named_nodes:
        print(f"Example named node: {named_nodes[0]} - {G.nodes[named_nodes[0]]['name']}")
else:
    print("Graph empty")
